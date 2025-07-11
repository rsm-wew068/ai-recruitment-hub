## Group Project GitHub repo for MGTA 495

This is repo for the Group Project in MGTA 495

### Command keyboard short-cut

Copy-and-pasting commands into a terminal can a bit cumbersome. To facilitate the process, you can add a keyboard shortcut to VS Code to send code to a terminal. Use the command palette and type "Preferences: Open Keyboard Shortcuts (JSON)". If this file is empty, you can copy and paste the below into the file and save it. If you already have shortcuts defined, add just the dictionary and save the file. Once the shortcut is defined, you can use ALT+Enter to send the command under the cursor to the terminal or you can select multiple lines to send. You can change "alt" to "cmd" or "ctrl" if you prefer.

```python
[
    {
        "key": "alt+enter",
        "command": "workbench.action.terminal.runSelectedText",
        "when": "editorLangId == 'shellscript' || editorLangId == 'markdown'"
    },
]
```

### Technical details

For Milestone 2 and beyond, we will be using UV for python package management. UV works on Windows, macOS, and Linux. First, open a terminal and determine if UV is already accessible:

```bash
uv --version
```

If you see a version number (e.g., 0.6.x), proceed to the next steps. If not, you can install `uv` using the command below. Only do this, however, if you don't already have UV installed:

```bash
pip install --user uv
```

**Setup the group repo**

First, make sure that you connected VS Code to the repo you cloned from GitHub (e.g., ~/.git/rsm-mgta495-xyz123). Then create a virtual environment using the command below:

```bash
uv venv --python 3.12.7  # Create virtual environment with Python 3.12.7
```

To use the environment in a terminal, you will need to `activate` it using the command below:

```bash
source .venv/bin/activate
```

**Package Management**

Once you have the basic setup done using the code chunk above you should be able to add python packages. The `pyrsm` package will install several dependencies that you will likely need (e.g., sklearn, pandas, etc.).

```bash
uv add pyrsm python-dotenv openai google-generativeai anthropic requests langchain langchain_openai langchain-google-genai langchain_anthropic langchain_community pydantic pydantic-ai ipywidgets
```

To double check if the package install worked as expected, run the command below.

```bash
uv run python -c "import requests; print(requests.__version__)"
```

In VS Code, you should now be able to select the `.venv` python environment to use in your Jupyter Notebooks.

**Using dotenv to manage API Keys**

Put the code below into a terminal and then copy in your API token for LLama. Make sure the API key is not shown *anywhere* in your code or notebooks! Also, NEVER push a `.env` file with keys, passwords, or secrets to GitHub.

```bash
echo "LLAMA_API_KEY=copy-your-api-token-here" >> ~/.env
```

You can get a free API key from Google Gemini at <https://aistudio.google.com/apikey>{target="_blank"}. You may need to use a personal Gmail account to access Google AI Studio. Once you have the key, add it to your `.env` file using the command below:

```bash
echo "GEMINI_API_KEY=copy-your-api-token-here" >> ~/.env
```

> Note: If you wan to double check if the keys were correctly added to your `.env` file, run the command below.

```bash
code ~/.env
```

**Push changes**

At this point, you can commit your changes to git. Before you run the code below, however, make sure there is not a `.env` file in your repo and that no jupyter notebooks show any of your API keys.

```bash
git add .
git commit -m "init 2025"
git push
```

### Using UV for other projects

The standard approach for projects will be to create a new folder and setup a virtual environment specifically for that project. For example, lets say your new project will be `test_project`. You could start with the commands below:

```
cd ~;
mkdir test_project;
cd test_project;
```

Then initialize your project environment:

```bash
uv init .                # Initialize UV in current directory
```

```bash
uv venv --python 3.12.7  # Create virtual environment with Python 3.12.7
```

In VS Code, you should be able to select the `.venv` python environment to use in your Jupyter Notebooks. To use the environment in a terminal, you will need to `activate` it using the command below:

```bash
source .venv/bin/activate
```

Then `add` the python packages you need just like we did above. If you plan to work with Jupyter notebooks (*.ipynb files) in your new project, you will need to install notebook dependencies using the below:

```bash
uv add ipykernel jupyter
```

Common UV commands for managing packages are listed below. Note that these will give directory specific results:

```bash
uv add <package-name>    # Install a package
uv remove <package-name> # Remove a package
uv pip list              # List installed packages in current directory
uv run python-file.py    # Run a Python file using the virtual environment
```

For more information about UV watch:

* <https://www.youtube.com/watch?v=qh98qOND6MI>{target="_blank"}
* <https://www.datacamp.com/tutorial/python-uv>{target="_blank"}
* <https://github.com/astral-sh/uv>{target="_blank"}

### Trouble shooting

If, for some reason, you want to reset the project, run the below to get to the project directory of your choice. Check that the `pwd` command shows you the directory you are trying to clean up.

```bash
cd ~/test_project
pwd
```

Then run the below. Note that is a DESTRUCTIVE operation. Double and triple check that only the things you want to remove are listed below. There is NO UNDO for this operation:

```bash
rm -rf .git .venv/ .python-version main.py pyproject.toml uv.lock
```
