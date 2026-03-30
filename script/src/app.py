from logger import get_logger
from config import cfg
from downloader import open_site
from pathlib import Path
from downloader import get_available_states
from states import LOCAL_STATES


class ScraperApp:
    """Orquestra execução do scraper.

    Responsabilidade: receber parâmetros e invocar `open_site()` que faz a automação.
    Mantemos a lógica de parsing/entrada em `main.py`.
    """

    def __init__(self, logger=None):
        if logger is None:
            log_path = Path(cfg.LOGS_DIR) / "app.log"
            logger = get_logger("scraper_app", log_path)
        self.logger = logger

    def run(self, selected_states=None, reset_checkpoint=None, concurrency=None):
        """Inicia a execução chamando `open_site`.

        Params:
            selected_states (set[str]|None): UFs selecionadas (ex: {'SP','MG'}) ou None para todos.
            reset_checkpoint (bool|None): Força reset do checkpoint (None para usar config default).
            concurrency (int|None): número de workers (None para usar config default).
        """
        self.logger.info(f"ScraperApp.run selected_states={selected_states} reset_checkpoint={reset_checkpoint} concurrency={concurrency}")
        open_site(selected_states=selected_states, reset_checkpoint=reset_checkpoint, concurrency=concurrency)

    def _parse_numeric_selection(self, items, prompt_text):
        print(prompt_text)
        for i, st in enumerate(items, start=1):
            print(f"{i}. {st}")
        choice = input("Escolha números separados por vírgula (ex: 1,2,3) ou pressione ENTER para todos: ").strip()
        if not choice:
            return None
        picks = set()
        parts = [p.strip() for p in choice.split(',') if p.strip()]
        for p in parts:
            try:
                idx = int(p)
                if 1 <= idx <= len(items):
                    picks.add(items[idx-1])
            except Exception:
                continue
        if not picks:
            return None
        return {s.split(' - ')[0].upper() for s in picks}

    def prompt_states(self, states_arg=None, interactive_flag=False):
        """Resolve a seleção de estados a partir de: `states_arg` (string ou set),
        `interactive_flag` (buscar lista ao vivo) ou prompt local.

        Retorna: `set` de códigos UF (ex: {'SP','MG'}) ou None para todos.
        """
        # if user passed --states as string, accept it
        if states_arg:
            # allow either a set provided already or a comma string
            if isinstance(states_arg, (set, list)):
                return {s.strip().upper() for s in states_arg}
            return {x.strip().upper() for x in str(states_arg).split(',') if x.strip()}

        # interactive flag: fetch live list from site (this opens browser)
        if interactive_flag:
            live = get_available_states()
            available = [a for a in live if a and 'selecione' not in a.lower()]
            if not available:
                print("Nenhum estado disponível para seleção.")
                return None
            return self._parse_numeric_selection(available, "Estados disponíveis (ao vivo):")

        # default: local list (no browser)
        return self._parse_numeric_selection(LOCAL_STATES, "Estados disponíveis:")
