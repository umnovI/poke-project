"""Tasks dependencies"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep


def user_confirm(question: str) -> bool:
    """Confirmation interface (y/n)

    Args:
        question (str): Input prompt.
    """

    reply = input(question + " ([y]/n): ").lower().strip()
    if reply in ("y", ""):
        return True
    if reply == "n":
        return False

    new_question = question
    if "Not valid response. " not in question:
        new_question = f"Not valid response. {question}"
    return user_confirm(new_question)


def date_checker(file_dir: str, period: float) -> tuple[bool, str]:
    """Check if now is more than last check time + period

    Args:
        file_dir (str): Where to keep date of the last check. Must be in .tmp directory.
        period (float): When date should be considered expired.

    Returns:
        tuple[bool, str]: Returns bool and a reason.
    """

    if os.path.exists(file_dir):
        with open(file_dir, encoding="utf-8") as existing_file:
            read_file = existing_file.read()
            if read_file:
                last_checked = datetime.fromisoformat(read_file)
            else:
                return (True, "Not found.")
        return (
            last_checked + timedelta(days=float(period)) <= datetime.now(),
            str(last_checked),
        )

    Path("./.tmp/").mkdir(parents=True, exist_ok=True)
    with open(file_dir, "w", encoding="utf-8") as out_file:
        out_file.write(datetime.now().isoformat())
    return (True, "Never.")


def set_timer(time: float = 60):
    """Set delay."""

    print(f"Setting delay for {time} seconds.")
    sleep(time)
    print("Time's up!")
