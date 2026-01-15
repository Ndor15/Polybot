# NBA Polymarket Trading Bot 🏀

Un bot de trading automatisé pour les marchés NBA sur Polymarket. Le bot analyse les matchs en direct, détecte des opportunités de trading basées sur des événements (momentum runs, changements de lead, etc.) et exécute des trades avec stop loss et take profit automatiques.

## 🎯 Stratégie de Trading

Le bot utilise plusieurs stratégies basées sur l'analyse des événements NBA en temps réel :

### 1. Fading Momentum Runs
- Détecte les runs de 8+ points sans réponse
- **Stratégie** : Parie CONTRE l'équipe en run (contrarian)
- **Logique** : Les runs s'arrêtent et les odds surréagissent

### 2. Fading Lead Changes
- Détecte les changements de lead significatifs (5+ points)
- **Stratégie** : Parie sur l'équipe qui vient de PERDRE le lead
- **Logique** : Les marchés paniquent, la variance se rééquilibre

### 3. Close Game Advantage
- Identifie les matchs serrés au 4e quart
- **Stratégie** : Légère préférence pour l'équipe à domicile
- **Logique** : Home court advantage dans les moments clés

### 4. Comeback Fading
- Détecte les comebacks majeurs
- **Stratégie** : Fade le comeback (parie contre)
- **Logique** : Les odds surréagissent au momentum

## 🚀 Installation

### Prérequis
- Python 3.8+
- Compte Polymarket avec wallet Polygon
- Clé API NBA (optionnel, tier gratuit disponible)

### Installation

```bash
# Cloner le repo
git clone <repo-url>
cd Polybot

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

## ⚙️ Configuration

1. Copier le fichier d'exemple :
```bash
cp .env.example .env
```

2. Éditer `.env` avec vos paramètres :

```bash
# Polymarket (REQUIS)
POLYMARKET_PRIVATE_KEY=votre_clé_privée_wallet

# NBA API (optionnel)
NBA_API_KEY=votre_clé_api  # Laisser vide pour tier gratuit

# Trading (ajuster selon votre profil de risque)
TRADE_SIZE_USDC=5.0
MAX_CONCURRENT_TRADES=3
STOP_LOSS_PERCENTAGE=2.5
TAKE_PROFIT_PERCENTAGE=3.0

# Signaux (ajuster pour sensibilité)
MOMENTUM_RUN_THRESHOLD=8
LEAD_CHANGE_THRESHOLD=5
UPDATE_INTERVAL_SECONDS=3
```

## 🎮 Utilisation

### Démarrer le bot

```bash
python bot.py
```

Le bot va :
1. Se connecter aux APIs NBA et Polymarket
2. Surveiller les matchs NBA en direct
3. Analyser les événements et générer des signaux
4. Exécuter des trades selon la stratégie
5. Gérer automatiquement les stop loss et take profit

### Arrêter le bot

Appuyer sur `Ctrl+C` pour un arrêt gracieux. Le bot fermera toutes les positions ouvertes et affichera les statistiques finales.

## 📊 Gestion des Risques

Le bot inclut plusieurs mécanismes de protection :

### Stop Loss & Take Profit
- **Stop Loss** : Ferme automatiquement à -2.5% (configurable)
- **Take Profit** : Ferme automatiquement à +3.0% (configurable)
- **Time Limit** : Ferme après 1 heure max (configurable)

### Limites de Position
- Maximum 3 positions simultanées (configurable)
- Pas de positions multiples sur le même match
- Taille de position basée sur la confiance du signal

### Contrôles de Portfolio
- Exposition totale limitée à 50 USDC
- Trading en pause si drawdown > 10%
- Alertes sur positions à risque

## 📁 Architecture

```
Polybot/
├── bot.py                 # Point d'entrée principal
├── config.py              # Configuration centralisée
├── nba_client.py          # Client API NBA (temps réel)
├── polymarket_client.py   # Client Polymarket (ordres)
├── signal_analyzer.py     # Moteur d'analyse de signaux
├── risk_manager.py        # Gestion des risques
├── requirements.txt       # Dépendances Python
├── .env.example          # Template de configuration
└── README.md             # Documentation
```

## 🔧 Modules

### `nba_client.py`
- Collecte les données de matchs en temps réel
- Tracking des scores, momentum, runs
- Détection de lead changes

### `signal_analyzer.py`
- Analyse les événements de jeu
- Génère des signaux de trading avec niveau de confiance
- 4 types de signaux : momentum, lead change, close game, comeback

### `polymarket_client.py`
- Connexion à l'API Polymarket
- Gestion des ordres (BUY/SELL)
- Tracking des positions avec P&L

### `risk_manager.py`
- Calcul de taille de position (Kelly-inspired)
- Vérification des limites de risque
- Statistiques de performance

## 📈 Métriques & Monitoring

Le bot affiche en temps réel :
- Positions actives et exposition
- P&L total et par position
- Win rate et statistiques de trading
- Alertes sur positions à risque

Logs détaillés dans `nba_polymarket_bot.log`

## ⚠️ Important

### Note sur l'implémentation
- **Version actuelle** : Mock trading (simulation)
- **Pour production** : Intégrer `py-clob-client` pour exécution réelle
- Les fonctions `place_order()` et `close_position()` sont des placeholders

### Mise en production

Pour utiliser en réel :
1. Installer `py-clob-client` : `pip install py-clob-client`
2. Implémenter l'authentification Polymarket dans `polymarket_client.py`
3. Remplacer les mock orders par des vrais appels API
4. Tester avec de petites sommes d'abord

### Avertissements
- **Trading à risque** : Vous pouvez perdre de l'argent
- **Pas de garantie** : Les stratégies ne sont pas infaillibles
- **Testez d'abord** : Utilisez de petites sommes pour débuter
- **Surveillez** : Gardez un œil sur le bot, bugs possibles

## 🧪 Tests

Tester les modules individuellement :

```bash
# Test NBA client
python nba_client.py

# Test signal analyzer
python signal_analyzer.py

# Test Polymarket client
python polymarket_client.py

# Test risk manager
python risk_manager.py
```

## 🛠️ Optimisation

Pour améliorer la rentabilité :

1. **Ajuster les seuils** : Modifier `MOMENTUM_RUN_THRESHOLD`, `LEAD_CHANGE_THRESHOLD`
2. **Backtesting** : Collecter des données historiques et backtester
3. **Machine Learning** : Entraîner un modèle sur les patterns gagnants
4. **Vitesse** : Optimiser la latence pour être plus rapide que le marché
5. **Diversification** : Ajouter d'autres sports (NFL, MLB, etc.)

## 📚 Ressources

### APIs
- [Polymarket Docs](https://docs.polymarket.com/)
- [BallDontLie NBA API](https://www.balldontlie.io/)
- [SportsDataIO](https://sportsdata.io/nba-api)

### Stratégies
- [NBA Momentum Betting](https://sportsepreneur.com/nba-art-momentum-betting-strategy/)
- [Live Betting Tactics](https://theleadsm.com/mastering-live-nba-betting-tools-and-tactics-for-lasting-success/)

## 📄 License

Educational purposes only. Trade at your own risk.

## 🤝 Contribution

Améliorations bienvenues ! Ouvrez une issue ou une pull request.

## 💬 Support

Pour questions ou bugs, ouvrez une issue sur GitHub.

---

**Disclaimer** : Ce bot est fourni à titre éducatif. Le trading comporte des risques de perte en capital. Utilisez à vos propres risques
