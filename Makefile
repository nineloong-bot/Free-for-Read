.PHONY: build build-macos build-linux build-windows clean

PYINSTALLER = uv run --extra dev pyinstaller

build:
	$(PYINSTALLER) --onefile \
		--name free-for-read \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

build-macos:
	$(PYINSTALLER) --onefile \
		--name free-for-read \
		--target-architecture universal2 \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

build-linux:
	$(PYINSTALLER) --onefile \
		--name free-for-read \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

build-windows:
	$(PYINSTALLER) --onefile \
		--name free-for-read \
		--noconsole \
		--hidden-import uvicorn.protocols.http.auto \
		--hidden-import uvicorn.loops.auto \
		free_for_read/cli.py

clean:
	rm -rf build/ dist/ *.spec
