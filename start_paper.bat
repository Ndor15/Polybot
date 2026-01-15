@echo off
REM Script de lancement rapide pour Windows
REM Double-clique sur ce fichier pour lancer le bot en mode paper

echo ========================================
echo  NBA Polymarket Bot - Paper Mode
echo ========================================
echo.

REM Vérifier si l'environnement virtuel existe
if not exist "venv\" (
    echo [SETUP] Creation de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo Erreur: Python n'est pas installe ou pas dans le PATH
        pause
        exit /b 1
    )
)

REM Activer l'environnement
echo [SETUP] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Installer/mettre à jour les dépendances
if not exist "venv\Lib\site-packages\colorlog\" (
    echo [SETUP] Installation des dependances...
    pip install -r requirements.txt
)

REM Créer .env s'il n'existe pas
if not exist ".env" (
    echo [SETUP] Creation du fichier .env...
    copy .env.paper .env
    echo Fichier .env cree avec configuration par defaut
)

echo.
echo ========================================
echo  Demarrage du bot en mode PAPER
echo ========================================
echo.
echo Balance de depart : $100 virtuels
echo Appuyez sur Ctrl+C pour arreter
echo.

REM Lancer le bot
python bot_v2.py --paper

REM Pause à la fin pour voir les messages
pause
