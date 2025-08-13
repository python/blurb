import os

from blurb._git import flush_git_add_files, git_add_files
from blurb._template import sanitize_section, sections


def populate() -> None:
    """Creates and populates the Misc/NEWS.d directory tree."""
    os.chdir('Misc')
    os.makedirs('NEWS.d/next', exist_ok=True)

    for section in sections:
        dir_name = sanitize_section(section)
        dir_path = f'NEWS.d/next/{dir_name}'
        os.makedirs(dir_path, exist_ok=True)
        readme_path = f'NEWS.d/next/{dir_name}/README.rst'
        with open(readme_path, 'w', encoding='utf-8') as readme:
            readme.write(
                f'Put news entry ``blurb`` files for the *{section}* section in this directory.\n'
            )
        git_add_files.append(dir_path)
        git_add_files.append(readme_path)
    flush_git_add_files()
