.PHONY: all

all: ../dist/main.py ../dist/app/__init__.py ../dist/app/api.py ../dist/app/hal.py ../dist/app/clock.py ../dist/app/self_test.py ../dist/app/settings.py ../dist/app/irrigation.py ../dist/static/index.html

../dist/main.py: main.py
	../install.sh ../dist/ main.py

../dist/app/__init__.py: app/__init__.py
	../install.sh ../dist/app/ app/__init__.py

../dist/app/api.py: app/api.py
	../install.sh ../dist/app/ app/api.py

../dist/app/hal.py: app/hal.py
	../install.sh ../dist/app/ app/hal.py

../dist/app/clock.py: app/clock.py
	../install.sh ../dist/app/ app/clock.py

../dist/app/self_test.py: app/self_test.py
	../install.sh ../dist/app/ app/self_test.py

../dist/app/settings.py: app/settings.py
	../install.sh ../dist/app/settings.py app/settings.py

../dist/app/irrigation.py: app/irrigation.py
	../install.sh ../dist/app/irrigation.py app/irrigation.py

../dist/static/index.html: static/index.html
	../copy.sh ../dist/static/index.html static/index.html
