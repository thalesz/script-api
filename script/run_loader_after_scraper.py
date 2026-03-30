import time
import subprocess
from pathlib import Path
from script.src.config import cfg
from script.src.logger import get_logger


logger = get_logger('loader-wait', Path(cfg.LOGS_DIR) / 'loader-wait.log')


def wait_for_sentinel(timeout=None, poll=2):
    sentinel = cfg.CHECKPOINT_DIR / 'scraper_done'
    logger.info(f'Waiting for sentinel: {sentinel}')
    waited = 0
    while True:
        if sentinel.exists():
            logger.info('Sentinel detected, starting loader')
            return True
        time.sleep(poll)
        if timeout:
            waited += poll
            if waited >= timeout:
                logger.error('Timeout waiting for sentinel')
                return False


def run_loader():
    # call the loader module as a script
    try:
        subprocess.run(['python', 'script/src/loader.py'], check=True)
    except subprocess.CalledProcessError as e:
        logger.exception('Loader process failed: %s', e)


if __name__ == '__main__':
    ok = wait_for_sentinel()
    if ok:
        run_loader()
