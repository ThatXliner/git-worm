from xclif import Cli

from . import routes

cli = Cli.from_routes(routes, local_config=".git-worm.toml")

if __name__ == "__main__":
    cli()
