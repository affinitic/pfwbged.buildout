#!/usr/bin/make

remove_duplicate_contacts:
	PYTHONIOENCODING=utf-8 ./bin/instance1 run ./scripts/remove_duplicate_contacts.py pfwbged

