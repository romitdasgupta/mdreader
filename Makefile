.PHONY: run test smoke build flatpak install uninstall

PYTHON ?= python3

run:
	$(PYTHON) -m folio

test:
	$(PYTHON) -m pytest -q

smoke:
	$(PYTHON) scripts/smoke_gui.py

build:
	$(PYTHON) -m build --no-isolation

flatpak:
	sh scripts/build_flatpak.sh

install:
	$(PYTHON) scripts/install_local.py

uninstall:
	$(PYTHON) scripts/install_local.py --uninstall
