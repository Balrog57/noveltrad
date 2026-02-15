@echo off
echo Creation de l'environnement virtuel...
python -m venv venv
call venv\Scripts\activate
echo Installation des dependances...
pip install -r requirements.txt
echo Termine ! Vous pouvez lancer l'application avec : run.bat
pause
