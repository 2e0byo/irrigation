.PHONY: all

all: ../dist/main.py ../dist/app/__init__.py ../dist/app/api.py ../dist/app/hal.py

../dist/main.py: main.py
	../install.sh ../dist/ main.py

../dist/app/__init__.py: app/__init__.py
	../install.sh ../dist/app/ app/__init__.py

../dist/app/api.py: app/api.py
	../install.sh ../dist/app/ app/api.py

../dist/app/hal.py: app/hal.py
	../install.sh ../dist/app/ app/hal.py
