import argparse
import os
from logger import get_logger
from config import cfg
from downloader import get_available_states
from states import LOCAL_STATES
from app import ScraperApp


def _parse_states_arg(s: str):
    return {x.strip().upper() for x in s.split(',') if x.strip()}


def main():
    parser = argparse.ArgumentParser(description="Scraper de Dados Abertos")
    parser.add_argument('--states', help='UFs separadas por vírgula, ex: SP,MG', default=None)
    parser.add_argument('--reset-checkpoint', action='store_true', help='Remover checkpoint antes de iniciar')
    parser.add_argument('--concurrency', type=int, help='Número de workers em paralelo')
    parser.add_argument('--interactive', action='store_true', help='Forçar prompt interativo de seleção')
    args = parser.parse_args()

    log_path = cfg.LOGS_DIR / "app.log"
    logger = get_logger("scraper", log_path)
    logger.info("Iniciando scraper")

    selected = None
    if args.states:
        selected = _parse_states_arg(args.states)

    app = ScraperApp(logger=logger)
    if not selected:
        # If user requested interactive selection, show live/local prompt
        if args.interactive:
            selected = app.prompt_states(states_arg=args.states, interactive_flag=True)
        else:
            # When running headless (env OR config) assume non-interactive container run => select ALL (None)
            headless_env = os.getenv('HEADLESS')
            headless_flag = (headless_env and str(headless_env).lower() in ('1', 'true', 'yes')) or cfg.HEADLESS
            if headless_flag:
                selected = None
            else:
                # local prompt fallback
                selected = app.prompt_states(states_arg=args.states, interactive_flag=False)

    # resolve reset_checkpoint: pass True when requested, else None to respect config default
    reset_arg = True if args.reset_checkpoint else None
    app.run(selected_states=selected, reset_checkpoint=reset_arg, concurrency=args.concurrency)

    # write a sentinel file so external loader services know scraper finished
    try:
        sentinel_dir = cfg.CHECKPOINT_DIR
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        sentinel = sentinel_dir / 'scraper_done'
        sentinel.write_text('ok')
        logger.info(f'Wrote sentinel {sentinel}')
    except Exception:
        logger.exception('Failed to write scraper completion sentinel')


if __name__ == '__main__':
    main()