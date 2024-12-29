# Subdomain for _wbgym.de_
This is the repository, where the Weinberg Secondary School develops a subdomain for their website wbgym.de.

# To Run
1. Install [uv](https://docs.astral.sh/uv/)
2. Clone this repo
3. In repo run `uv run flask --app subdomain/app run --debug`
4. This will start a flask development server, that will refresh on file changes.
5. To build: `docker build -t subdomain:[APPROPRIATE TAG] .`