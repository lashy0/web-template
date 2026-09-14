import asyncio

from app.bootstrap.application import bootstrap_first_administrator

if __name__ == "__main__":
    asyncio.run(bootstrap_first_administrator())
