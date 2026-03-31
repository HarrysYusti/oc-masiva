@echo off
echo =======================================================
echo Iniciando Playwright Codegen (Grabador de Acciones)
echo =======================================================
echo.
echo Se abrira un navegador donde podras realizar acciones
echo y se generara el codigo de Playwright correspondiente.
echo.
python -m playwright codegen https://natura.coupahost.com/
pause
