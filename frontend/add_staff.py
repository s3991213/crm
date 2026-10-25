"""Add or reset a staff login.

The password you set here is temporary: the staff member is asked to choose
their own the first time they sign in.

Removing or resetting a login signs that person out of any open session.

Usage:
    python add_staff.py <username> "<Full Name>"
    python add_staff.py --remove <username>
"""

import getpass
import sys

from staff_auth import remove_staff, set_staff


def main() -> None:
    args = sys.argv[1:]

    if len(args) == 2 and args[0] == "--remove":
        username = args[1].strip().lower()
        if remove_staff(username):
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

    set_staff(username, name, password)
    print(f"Saved login '{username}' for {name}.")
    print("Give them the username and temporary password. They'll choose their own when they first sign in.")


if __name__ == "__main__":
    main()
