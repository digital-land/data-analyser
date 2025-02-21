from flask.cli import AppGroup

cli = AppGroup("cli")


@cli.command("hello")
def hello():
    print("Hello, world!")
