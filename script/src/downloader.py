from playwright.sync_api import sync_playwright
from config import cfg
from logger import get_logger
from states import LOCAL_STATES
import os
import re
import time
import unicodedata
from pathlib import Path
import concurrent.futures


class Downloader:
    """Full Downloader class encapsulating the download workflow.

    Module-level functions at the bottom keep backward compatibility by
    instantiating this class and delegating calls to its methods.
    """

    def __init__(self,
                 base_url=cfg.BASE_URL,
                 headless=cfg.HEADLESS,
                 download_dir=cfg.DOWNLOAD_DIR,
                 max_attempts=cfg.MAX_ATTEMPTS,
                 download_timeout=cfg.DOWNLOAD_TIMEOUT,
                 short_sleep=cfg.SHORT_SLEEP,
                 checkpoint_dir=cfg.CHECKPOINT_DIR,
                 logs_dir=cfg.LOGS_DIR,
                 reset_checkpoint=cfg.RESET_CHECKPOINT,
                 concurrency=cfg.CONCURRENCY,
                 state_retry_rounds=cfg.STATE_RETRY_ROUNDS):
        self.base_url = base_url
        self.headless = headless
        self.download_dir = download_dir
        self.max_attempts = max_attempts
        self.download_timeout = download_timeout
        self.short_sleep = short_sleep
        self.checkpoint_dir = Path(checkpoint_dir)
        self.logs_dir = Path(logs_dir)
        self.reset_checkpoint = reset_checkpoint
        self.concurrency = concurrency
        self.state_retry_rounds = max(0, int(state_retry_rounds))
        # respect HEADLESS environment variable when present (docker-compose sets HEADLESS=true)
        env_headless = os.getenv('HEADLESS')
        if env_headless is not None:
            try:
                headless = str(env_headless).lower() in ('1', 'true', 'yes')
            except Exception:
                headless = headless

        self.headless = headless
        self.logger = get_logger('downloader', self.logs_dir / 'app.log')

    @staticmethod
    def _safe_filename(s: str) -> str:
        normalized = unicodedata.normalize('NFKD', s)
        ascii_text = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        return re.sub(r"[^A-Za-z0-9_-]", "_", ascii_text).strip("_")

    def _load_checkpoint(self, ck_file: Path):
        try:
            import json
            if ck_file.exists():
                with ck_file.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data if isinstance(data, list) else [])
        except Exception as e:
            print('Aviso: falha ao ler checkpoint:', e)
        return set()

    def _save_checkpoint(self, ck_file: Path, completed_states: set):
        try:
            import json
            tmp = ck_file.with_suffix('.tmp')
            with tmp.open('w', encoding='utf-8') as f:
                json.dump(sorted(list(completed_states)), f, ensure_ascii=False, indent=2)
            tmp.replace(ck_file)
        except Exception as e:
            print('Aviso: falha ao salvar checkpoint:', e)

    def _mark_completed(self, ck_file: Path, completed_states: set, state_name: str):
        completed_states.add(state_name)
        self._save_checkpoint(ck_file, completed_states)

    def _count_csv_records(self, path: str) -> int:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                total = sum(1 for _ in f)
                return max(0, total - 1)
        except Exception:
            return -1

    def _validate_checkpoint_files(self, completed_states: set, out_dir: str):
        removed = False
        for st in list(completed_states):
            fname = self._safe_filename(st) + '.csv'
            p = os.path.join(out_dir, fname)
            try:
                if not os.path.exists(p) or os.path.getsize(p) == 0:
                    print(f"Checkpoint cleanup: arquivo ausente/vazio para {st}, removendo do checkpoint")
                    completed_states.remove(st)
                    removed = True
            except Exception:
                completed_states.remove(st)
                removed = True
        return removed

    def worker_process_state(self, task):
        opt_text, opt_value, out_dir = task
        result = {"state": opt_text, "success": False, "out_path": None, "records": -1, "error": None, "skipped": False}
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                try:
                    page.goto(self.base_url, wait_until="networkidle")

                    page.wait_for_selector("div.card:has-text('Dados Abertos')", timeout=10000)
                    page.click("div.card:has-text('Dados Abertos')")
                    page.wait_for_load_state('networkidle')

                    uf_code = (opt_text.split(' - ')[0].strip().upper() if opt_text else '').strip()
                    selected_ok = False
                    for candidate in [opt_value, uf_code]:
                        if not candidate:
                            continue
                        try:
                            page.select_option('select', candidate)
                            selected_ok = True
                            break
                        except Exception:
                            continue

                    if not selected_ok:
                        selected_ok = bool(page.evaluate(
                            """(uf, label) => {
                                const s = document.querySelector('select');
                                if (!s) return false;
                                const norm = (x) => (x || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim();
                                const targetUf = norm(uf);
                                const targetLabel = norm(label);
                                const options = Array.from(s.options || []);
                                let match = options.find(o => norm(o.value) === targetUf);
                                if (!match) match = options.find(o => norm(o.textContent).startsWith(targetUf + ' -'));
                                if (!match) match = options.find(o => norm(o.textContent) === targetLabel);
                                if (!match) return false;
                                s.value = match.value;
                                s.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }""",
                            uf_code,
                            opt_text,
                        ))

                    if not selected_ok:
                        raise RuntimeError(f'Não foi possível selecionar estado: {opt_text}')

                    page.wait_for_load_state('networkidle')

                    try:
                        page.evaluate("() => { const sels = document.querySelectorAll('select'); if(sels.length>1){ const m = sels[1]; const opt = Array.from(m.options).find(o=>/Todos os municípios/i.test(o.textContent)); if(opt){ m.value = opt.value; m.dispatchEvent(new Event('change',{bubbles:true})); } } }")
                        page.wait_for_load_state('networkidle')
                    except Exception:
                        pass

                    fill_captcha_js = '''(digits) => {
                        const sels = ["input[placeholder*='dígitos']", "input[placeholder*='Digite']", "input[id*='captcha']", "input[name*='captcha']"];
                        for (const sel of sels) {
                            const el = document.querySelector(sel);
                            if (el) { el.value = digits; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); return true; }
                        }
                        return false;
                    }'''

                    refresh_captcha_js = '''() => {
                        const sels = ["button.captcha-refresh", ".captcha-refresh", "a.captcha-refresh", "button[title*='Atualizar']", "button[aria-label*='refresh']"];
                        for (const sel of sels) { const el = document.querySelector(sel); if (el) { try { el.click(); return true;} catch(e){} } }
                        const icons = Array.from(document.querySelectorAll('*')).filter(n => /[↻⟳]/.test(n.textContent)); if (icons.length) { try { icons[0].click(); return true;} catch(e){} }
                        return false; }'''

                    attempt = 0
                    while attempt < self.max_attempts:
                        attempt += 1
                        try:
                            captcha_text = page.evaluate("() => document.querySelector('#captcha-text-export')?.innerText || ''")
                            digits = re.sub(r"\D", "", captcha_text)
                            if not digits:
                                page.evaluate(refresh_captcha_js)
                                time.sleep(self.short_sleep)
                                continue

                            page.evaluate(fill_captcha_js, digits)
                            download_el = page.query_selector("button:has-text('Baixar CSV')") or page.query_selector("button:has-text('Baixar')")
                            if not download_el:
                                result['error'] = 'Botão de download não encontrado'
                                break

                            try:
                                with page.expect_download(timeout=min(3000, self.download_timeout)) as dlf:
                                    download_el.click()
                                dl = dlf.value
                                safe_name = self._safe_filename(opt_text)
                                out_path = os.path.join(out_dir, f"{safe_name}.csv")
                                dl.save_as(out_path)
                                result['success'] = True
                                result['out_path'] = out_path
                                try:
                                    with open(out_path, 'r', encoding='utf-8') as f:
                                        total = sum(1 for _ in f)
                                        result['records'] = max(0, total - 1)
                                except Exception:
                                    result['records'] = -1
                                break
                            except Exception:
                                try:
                                    with page.expect_download(timeout=self.download_timeout) as dlf:
                                        try:
                                            download_el.click()
                                        except Exception:
                                            pass
                                    dl = dlf.value
                                    safe_name = self._safe_filename(opt_text)
                                    out_path = os.path.join(out_dir, f"{safe_name}.csv")
                                    dl.save_as(out_path)
                                    result['success'] = True
                                    result['out_path'] = out_path
                                    try:
                                        with open(out_path, 'r', encoding='utf-8') as f:
                                            total = sum(1 for _ in f)
                                            result['records'] = max(0, total - 1)
                                    except Exception:
                                        result['records'] = -1
                                    break
                                except Exception:
                                    page.evaluate(refresh_captcha_js)
                                    time.sleep(self.short_sleep)
                                    continue

                        except Exception as e:
                            result['error'] = str(e)
                            page.evaluate(refresh_captcha_js)
                            time.sleep(self.short_sleep)
                            continue

                finally:
                    try:
                        page.close()
                    except Exception:
                        pass
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        browser.close()
                    except Exception:
                        pass

            return result
        except Exception as e:
            result['error'] = str(e)
            return result

    def get_available_states(self, timeout=10000):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context()
                page = context.new_page()
                page.goto(self.base_url, wait_until="networkidle")
                try:
                    page.wait_for_selector("div.card:has-text('Dados Abertos')", timeout=timeout)
                    page.click("div.card:has-text('Dados Abertos')")
                    page.wait_for_load_state('networkidle')
                except Exception:
                    try:
                        page.reload()
                        page.wait_for_load_state('networkidle')
                    except Exception:
                        pass
                opts = page.evaluate("() => { const s = document.querySelector('select'); if(!s) return []; return Array.from(s.options).map(o=>o.textContent.trim()).filter(t=>t); }")
                try:
                    page.close()
                except Exception:
                    pass
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass
                return opts
        except Exception:
            return []

    def open_site(self, selected_states=None, reset_checkpoint=None, concurrency=None):
        out_dir = str(Path(self.download_dir))
        os.makedirs(out_dir, exist_ok=True)

        if reset_checkpoint is None:
            reset_checkpoint = self.reset_checkpoint
        if concurrency is None:
            concurrency = self.concurrency

        self.logger.info(f"Resolved reset_checkpoint={reset_checkpoint} (config default={self.reset_checkpoint}), concurrency={concurrency}")

        # Fast path: when states are explicitly provided, skip the prefetch browser.
        # We can build tasks from LOCAL_STATES and let each worker resolve/select UF.
        if selected_states:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            ck_file = self.checkpoint_dir / "checkpoint.json"
            self.logger.info(f"Checkpoint file path: {ck_file}, exists={ck_file.exists()}")
            if reset_checkpoint:
                if ck_file.exists():
                    try:
                        ck_file.unlink()
                        self.logger.info('RESET_CHECKPOINT=True: checkpoint removido, iniciando do zero')
                    except Exception as e:
                        self.logger.warning(f'Falha ao remover checkpoint: {e}')
                completed_states = set()
            else:
                completed_states = self._load_checkpoint(ck_file)
                if self._validate_checkpoint_files(completed_states, out_dir):
                    self._save_checkpoint(ck_file, completed_states)

            state_label_map = {}
            for item in LOCAL_STATES:
                parts = item.split(' - ', 1)
                uf = parts[0].strip().upper()
                state_label_map[uf] = item

            tasks = []
            for uf in sorted({s.strip().upper() for s in selected_states if s}):
                state_label = state_label_map.get(uf, uf)
                if state_label in completed_states:
                    print(f"Pulando estado já processado (checkpoint): {state_label}")
                    continue
                tasks.append((state_label, uf, out_dir))

            def execute_tasks_round(task_batch):
                failed_tasks = []
                workers = concurrency if (concurrency and concurrency > 0) else 1
                self.logger.info(f'Executando workers em processo separado com {workers} workers, total tasks={len(task_batch)}')
                with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
                    futures = {ex.submit(_worker_process_state, t): t for t in task_batch}
                    for fut in concurrent.futures.as_completed(futures):
                        task = futures[fut]
                        st = task[0]
                        try:
                            res = fut.result()
                        except Exception as e:
                            self.logger.warning(f'Worker falhou para {st}: {e}')
                            failed_tasks.append(task)
                            continue
                        if res.get('success'):
                            out_path = res.get('out_path')
                            if not out_path or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                                self.logger.warning(f"Arquivo inválido para {st}; será tentado novamente")
                                failed_tasks.append(task)
                                continue
                            self.logger.info(f"Worker sucesso: {res['state']} -> {out_path} ({res.get('records')} registros)")
                            try:
                                self._mark_completed(ck_file, completed_states, res['state'])
                            except Exception as e:
                                self.logger.warning(f'Falha ao marcar checkpoint para {res["state"]}: {e}')
                        else:
                            self.logger.warning(f"Worker falhou para {res.get('state')}: {res.get('error')}")
                            failed_tasks.append(task)
                return failed_tasks

            pending = tasks
            max_rounds = self.state_retry_rounds + 1
            for round_idx in range(max_rounds):
                if not pending:
                    break
                if round_idx == 0:
                    self.logger.info(f"Iniciando round principal com {len(pending)} estados")
                else:
                    self.logger.info(f"Retry round {round_idx}/{self.state_retry_rounds} com {len(pending)} estados")
                pending = execute_tasks_round(pending)

            if pending:
                failed_names = [t[0] for t in pending]
                self.logger.error(f"Estados com falha após retries: {failed_names}")
                print(f"Estados com falha após retries: {', '.join(failed_names)}")
            else:
                self.logger.info('Todos os estados pendentes foram processados com sucesso')

            return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            page.goto(self.base_url, wait_until="networkidle")

            print("Título da página:", page.title())
            print("URL atual:", page.url)

            # screenshots removed for headless/container runs
            # page.screenshot(path=os.path.join(out_dir, "home.png"), full_page=True)

            try:
                page.wait_for_selector("div.card:has-text('Dados Abertos')", timeout=10000)
                page.click("div.card:has-text('Dados Abertos')")
                page.wait_for_load_state("networkidle")
                # page.screenshot(path=os.path.join(out_dir, "dados_abertos.png"), full_page=True)
                print("Entrou em Dados Abertos")
            except Exception as e:
                print("Não foi possível entrar em Dados Abertos:", e)
                if not self.headless:
                    try:
                        input("Pressione ENTER para fechar...")
                    except Exception:
                        pass
                browser.close()
                return

            try:
                state_options = page.evaluate("() => { const s = document.querySelector('select'); if(!s) return []; return Array.from(s.options).map(o=>({text: o.textContent.trim(), value: o.value})); }")
                if not state_options:
                    raise RuntimeError("Não foram encontrados estados na página")

                fill_captcha_js = '''(digits) => {
                    const sels = ["input[placeholder*='dígitos']", "input[placeholder*='Digite']", "input[id*='captcha']", "input[name*='captcha']"];
                    for (const sel of sels) {
                        const el = document.querySelector(sel);
                        if (el) {
                            el.value = digits;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                    }
                    return false;
                }'''

                self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
                ck_file = self.checkpoint_dir / "checkpoint.json"
                self.logger.info(f"Checkpoint file path: {ck_file}, exists={ck_file.exists()}")
                if reset_checkpoint:
                    if ck_file.exists():
                        try:
                            ck_file.unlink()
                            self.logger.info('RESET_CHECKPOINT=True: checkpoint removido, iniciando do zero')
                        except Exception as e:
                            self.logger.warning(f'Falha ao remover checkpoint: {e}')
                    completed_states = set()
                else:
                    completed_states = self._load_checkpoint(ck_file)
                    if self._validate_checkpoint_files(completed_states, out_dir):
                        self._save_checkpoint(ck_file, completed_states)

                refresh_captcha_js = '''() => {
                    const sels = ["button.captcha-refresh", ".captcha-refresh", "a.captcha-refresh", "button[title*='Atualizar']", "button[aria-label*='refresh']"];
                    for (const sel of sels) {
                        const el = document.querySelector(sel);
                        if (el) { try { el.click(); return true;} catch(e){} }
                    }
                    const icons = Array.from(document.querySelectorAll('*')).filter(n => /[↻⟳]/.test(n.textContent));
                    if (icons.length) { try { icons[0].click(); return true;} catch(e){} }
                    return false;
                }'''

                tasks = []
                for opt in state_options:
                    opt_text = opt.get('text')
                    opt_value = opt.get('value')
                    if not opt_value or 'Selecione' in opt_text or opt_text == '':
                        continue
                    if selected_states:
                        if opt_text.upper() not in selected_states and opt_text.split(' - ')[0].upper() not in selected_states:
                            continue
                    if opt_text in completed_states:
                        print(f"Pulando estado já processado (checkpoint): {opt_text}")
                        continue
                    tasks.append((opt_text, opt_value, out_dir))

                def execute_tasks_round(task_batch):
                    failed_tasks = []
                    workers = concurrency if (concurrency and concurrency > 0) else 1
                    self.logger.info(f'Executando workers em processo separado com {workers} workers, total tasks={len(task_batch)}')
                    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
                        futures = {ex.submit(_worker_process_state, t): t for t in task_batch}
                        for fut in concurrent.futures.as_completed(futures):
                            task = futures[fut]
                            st = task[0]
                            try:
                                res = fut.result()
                            except Exception as e:
                                self.logger.warning(f'Worker falhou para {st}: {e}')
                                failed_tasks.append(task)
                                continue
                            if res.get('success'):
                                out_path = res.get('out_path')
                                if not out_path or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
                                    self.logger.warning(f"Arquivo inválido para {st}; será tentado novamente")
                                    failed_tasks.append(task)
                                    continue
                                self.logger.info(f"Worker sucesso: {res['state']} -> {out_path} ({res.get('records')} registros)")
                                try:
                                    self._mark_completed(ck_file, completed_states, res['state'])
                                except Exception as e:
                                    self.logger.warning(f'Falha ao marcar checkpoint para {res["state"]}: {e}')
                            else:
                                self.logger.warning(f"Worker falhou para {res.get('state')}: {res.get('error')}")
                                failed_tasks.append(task)
                    return failed_tasks

                try:
                    try:
                        page.close()
                    except Exception:
                        pass
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        browser.close()
                    except Exception:
                        pass
                except Exception:
                    pass

                pending = tasks
                max_rounds = self.state_retry_rounds + 1
                for round_idx in range(max_rounds):
                    if not pending:
                        break
                    if round_idx == 0:
                        self.logger.info(f"Iniciando round principal com {len(pending)} estados")
                    else:
                        self.logger.info(f"Retry round {round_idx}/{self.state_retry_rounds} com {len(pending)} estados")
                    pending = execute_tasks_round(pending)

                if pending:
                    failed_names = [t[0] for t in pending]
                    self.logger.error(f"Estados com falha após retries: {failed_names}")
                    print(f"Estados com falha após retries: {', '.join(failed_names)}")
                else:
                    self.logger.info('Todos os estados pendentes foram processados com sucesso')

            except Exception as e:
                print("Erro ao iterar estados:", e)

            # only wait for user input when running in non-headless interactive mode
            if not self.headless:
                try:
                    input("Processamento finalizado. Pressione ENTER para fechar...")
                except Exception:
                    pass


# Module-level compatibility functions
def _worker_process_state(task):
    d = Downloader()
    return d.worker_process_state(task)


def get_available_states(timeout=10000):
    d = Downloader()
    return d.get_available_states(timeout=timeout)


def open_site(selected_states=None, reset_checkpoint=None, concurrency=None):
    d = Downloader()
    return d.open_site(selected_states=selected_states, reset_checkpoint=reset_checkpoint, concurrency=concurrency)


if __name__ == '__main__':
    import sys
    # If specific states are passed as arguments, use them; otherwise download all
    selected_states = None
    if len(sys.argv) > 1:
        selected_states = set(arg.upper() for arg in sys.argv[1:])
    
    d = Downloader()
    d.open_site(selected_states=selected_states)
