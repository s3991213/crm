"""Add or reset a staff login.

The password you set here is temporary: the staff member is asked to choose
their own the first time they sign in.

Usage:
    python add_staff.py <username> "<Full Name>"
    python add_staff.py --remove <username>
"""

import getpass
import sys

from staff_auth import hash_password, load_staff, save_staff


def main() -> None:
    args = sys.argv[1:]
    staff = load_staff()

    if len(args) == 2 and args[0] == "--remove":
        username = args[1].strip().lower()
        if staff.pop(username, None):
            save_staff(staff)
            print(f"Removed {username}.")
        else:
            print(f"No login called {username}.")
        return

    if len(args) != 2:
        print(__doc__)
        sys.exit(1)

    username, name = args[0].strip().lower(), args[1].strip()
    password = getpass.getpass(f"Temporary password for {name}: ")
    if len(password) < 8:
        print("Please use at least 8 characters.")
        sys.exit(1)
    if password != getpass.getpass("Type it again: "):
        print("Passwords did not match.")
        sys.exit(1)

    staff[username] = {"name": name, "password_hash": hash_password(password), "must_change": True}
    save_staff(staff)
    print(f"Saved login '{username}' for {name}.")
    print("Give them the username and temporary password. They'll choose their own when they first sign in.")


if __name__ == "__main__":
    main()
