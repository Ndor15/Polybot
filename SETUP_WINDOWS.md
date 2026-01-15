# 🪟 Setup Windows - NBA Polymarket Bot

Guide spécifique pour **installer et lancer le bot sur Windows**.

## ⚠️ Problèmes Connus sur Windows

1. **Emojis dans la console** : Corrigé dans la dernière version
2. **Encodage des fichiers** : Le bot gère maintenant UTF-8 automatiquement
3. **API NBA** : Nécessite une clé API gratuite

---

## 🚀 Installation Rapide (5 minutes)

### Étape 1 : Vérifier Python

Ouvre **PowerShell** ou **CMD** et tape :

```powershell
python --version
```

Tu dois voir `Python 3.8` ou plus récent. Sinon, [télécharge Python](https://www.python.org/downloads/).

⚠️ **Pendant l'installation, coche "Add Python to PATH"**

### Étape 2 : Naviguer vers le Projet

```powershell
cd C:\Users\<ton-nom>\Desktop\Polybot
```

Remplace `<ton-nom>` par ton nom d'utilisateur Windows.

### Étape 3 : Créer l'Environnement Virtuel

```powershell
python -m venv venv
```

### Étape 4 : Activer l'Environnement

```powershell
venv\Scripts\activate
```

Tu verras `(venv)` apparaître dans ton terminal.

### Étape 5 : Installer les Dépendances

```powershell
pip install -r requirements.txt
```

Ça prend 1-2 minutes.

### Étape 6 : Créer le Fichier .env (Optionnel pour Paper Mode)

Pour le **paper mode** (simulation), tu n'as pas besoin de clé API NBA **SI** tu acceptes que le bot attende les matchs.

Crée un fichier `.env` vide :

```powershell
copy .env.example .env
```

Ou crée un fichier `.env` avec juste :

```
# Pas besoin de clés pour paper mode
# Le bot attendra qu'un match commence
```

### Étape 7 : Lancer le Bot en Paper Mode

```powershell
python bot_v2.py --paper
```

**C'est tout !** Le bot va démarrer avec $100 virtuels.

---

## 🔑 Obtenir une Clé API NBA (Gratuit)

Pour que le bot puisse voir les matchs NBA en direct :

### 1. Va sur BallDontLie

Ouvre ton navigateur : https://www.balldontlie.io/

### 2. Crée un Compte Gratuit

Clique sur **"Get Started Free"** et inscris-toi.

### 3. Copie ta Clé API

Une fois connecté, copie ta clé API (ressemble à `abc123xyz...`).

### 4. Ajoute-la au Fichier .env

Ouvre `.env` avec Notepad et ajoute :

```
NBA_API_KEY=ta_clé_api_ici
```

Sauvegarde le fichier.

### 5. Relance le Bot

```powershell
python bot_v2.py --paper
```

Maintenant le bot pourra voir les matchs NBA !

---

## 🐛 Problèmes Courants Windows

### "python n'est pas reconnu"

**Solution** : Python n'est pas dans le PATH.

1. Réinstalle Python
2. **Coche "Add Python to PATH"** pendant l'installation
3. Redémarre ton terminal

Ou utilise :
```powershell
py -m venv venv
py bot_v2.py --paper
```

### "Cannot be loaded because running scripts is disabled"

**Solution** : PowerShell bloque les scripts.

**Option A** : Utilise CMD à la place de PowerShell

**Option B** : Active les scripts dans PowerShell (Admin) :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Puis relance :
```powershell
venv\Scripts\activate
```

### "No module named 'xyz'"

**Solution** : Dépendances mal installées.

```powershell
# Réactive l'environnement
venv\Scripts\activate

# Réinstalle
pip install -r requirements.txt
```

### "UnicodeEncodeError" dans les logs

**Solution** : Déjà corrigé dans la dernière version ! Fais :

```powershell
git pull
```

Ou télécharge la dernière version.

### "401 Unauthorized" pour NBA API

**Solution** : Tu as besoin d'une clé API (voir section "Obtenir une Clé API NBA" ci-dessus).

---

## 🎮 Commandes Utiles Windows

```powershell
# Activer l'environnement virtuel
venv\Scripts\activate

# Lancer en mode paper
python bot_v2.py --paper

# Lancer avec solde custom
python bot_v2.py --paper --balance 500

# Voir les logs en temps réel
Get-Content nba_polymarket_bot.log -Wait

# Arrêter le bot
Ctrl+C

# Désactiver l'environnement
deactivate
```

---

## 📝 Fichier .env Minimal pour Paper Mode

Contenu minimal (pas de clé NBA) :

```bash
# Configuration minimale pour paper mode

# NBA API (optionnel - obtiens une clé gratuite sur balldontlie.io)
# NBA_API_KEY=ta_clé_ici

# Trading (valeurs par défaut, ajuste si besoin)
TRADE_SIZE_USDC=5.0
MAX_CONCURRENT_TRADES=3
STOP_LOSS_PERCENTAGE=2.5
TAKE_PROFIT_PERCENTAGE=3.0

# Signaux
MOMENTUM_RUN_THRESHOLD=8
LEAD_CHANGE_THRESHOLD=5
```

---

## 🚦 Test de l'Installation

Pour vérifier que tout fonctionne :

```powershell
# Test du paper trader
python paper_trader.py

# Test du market matcher
python market_matcher.py

# Lancer le bot
python bot_v2.py --paper
```

Si tu vois des emojis colorés et aucune erreur, **tout est bon** ! 🎉

---

## 💰 Pour Passer en Live Trading (Plus Tard)

Quand tu seras prêt pour le trading réel :

1. **Obtiens un wallet Polygon avec USDC**
2. **Exporte ta clé privée** depuis MetaMask
3. **Ajoute-la au .env** :
   ```
   POLYMARKET_PRIVATE_KEY=0xta_clé_privée
   ```
4. **Lance en mode live** :
   ```powershell
   python bot_v2.py --live
   ```

⚠️ **Ne fais ça qu'après avoir été profitable en paper mode !**

---

## 🆘 Besoin d'Aide ?

1. Vérifie les logs : `type nba_polymarket_bot.log`
2. Consulte `QUICKSTART.md`
3. Lis `README_V2.md` pour les détails

---

## ✅ Checklist Installation Windows

- [ ] Python 3.8+ installé (avec PATH)
- [ ] Environnement virtuel créé (`venv`)
- [ ] Environnement activé (`venv\Scripts\activate`)
- [ ] Dépendances installées (`pip install -r requirements.txt`)
- [ ] Fichier `.env` créé (optionnel pour paper)
- [ ] Clé API NBA obtenue (optionnel)
- [ ] Bot lancé avec `python bot_v2.py --paper`
- [ ] Aucune erreur Unicode

**Tout est coché ? Tu es prêt à trader ! 🚀**

---

**Bon trading sur Windows ! 🪟🏀**
