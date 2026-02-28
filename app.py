def load_dotenv_if_available() -> None:
	try:
		dotenv_module = __import__("dotenv")
	except ModuleNotFoundError:
		return

	dotenv_module.load_dotenv()

from src import create_app

load_dotenv_if_available()

app = create_app()


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5001)
