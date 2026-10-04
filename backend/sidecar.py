import os

import uvicorn

from app.main import app


if __name__ == '__main__':
    port = int(os.getenv('WINGENT_BACKEND_PORT', '8000'))
    if not 1 <= port <= 65535:
        raise ValueError('WINGENT_BACKEND_PORT must be a valid TCP port.')
    uvicorn.run(app, host='127.0.0.1', port=port, log_level='warning')
