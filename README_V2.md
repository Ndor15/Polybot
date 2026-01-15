# NBA Polymarket Trading Bot V2 🏀💎

Un bot de trading automatisé **amélioré** pour les marchés NBA sur Polymarket avec mode paper trading, matching intelligent, et optimisation des paramètres.

## 🆕 Nouveautés Version 2

### 🧪 Mode Paper Trading
- **Testez sans risque** avec un solde virtuel
- Simulation réaliste avec slippage
- Analytics détaillées et export JSON
- Parfait pour tester des stratégies

### 💰 Trading Réel avec py-clob-client
- Intégration complète avec l'API Polymarket CLOB
- Authentification sécurisée L1/L2
- Ordres réels avec gestion des fills
- Vérification du solde en temps réel

### 🎯 Market Matching Intelligent
- Normalisation des noms d'équipes (LAL, Lakers, Los Angeles Lakers → Lakers)
- Matching fuzzy entre jeux NBA et marchés Polymarket
- Score de confiance pour chaque match
- Cache pour performance optimale

### 📊 Optimisation des Paramètres
- Grid search automatique pour trouver les meilleurs seuils
- Test de multiples combinaisons de paramètres
- Scoring composite (P&L + Win Rate + Sharpe)
- Export des résultats pour analyse

## 🚀 Installation Rapide

```bash
# Cloner et installer
git clone <repo>
cd Polybot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Éditer .env avec votre clé si trading réel
```

## 🎮 Utilisation

### Mode Paper Trading (Recommandé pour débuter)

```bash
# Démarrer en mode paper avec $100 virtuel
python bot_v2.py --paper

# Ou avec un solde custom
python bot_v2.py --paper --balance 500
```

Le bot va :
- ✅ Trader avec argent virtuel
- ✅ Simuler fills réalistes avec slippage
- ✅ Exporter les résultats en JSON
- ✅ Afficher analytics complètes

### Mode Live Trading (Après tests paper)

```bash
# ATTENTION : Trading réel avec vraie argent
python bot_v2.py --live
```

Prérequis:
- ✅ Avoir installé `py-clob-client`
- ✅ Avoir configuré `POLYMARKET_PRIVATE_KEY` dans `.env`
- ✅ Avoir des USDC sur Polygon
- ✅ Avoir testé en mode paper d'abord

### Optimisation des Paramètres

```bash
# Trouver les meilleurs paramètres
python optimizer.py
```

Va tester différentes combinaisons et recommander les meilleurs settings.

## 📁 Architecture V2

```
Polybot/
├── bot.py                 # Bot original (V1)
├── bot_v2.py             # Bot amélioré (V2) ⭐ NOUVEAU
├── config.py              # Configuration centralisée
├── nba_client.py          # Client API NBA
├── signal_analyzer.py     # Moteur de signaux
├── risk_manager.py        # Gestion des risques
│
├── polymarket_client.py   # Client simple (V1)
├── polymarket_trader.py   # Client réel py-clob ⭐ NOUVEAU
├── paper_trader.py        # Simulateur paper ⭐ NOUVEAU
├── market_matcher.py      # Matching intelligent ⭐ NOUVEAU
├── optimizer.py           # Optimisation params ⭐ NOUVEAU
│
├── requirements.txt       # Dépendances
├── .env.example          # Template config
└── README.md             # Documentation
```

## 🔧 Nouveaux Modules

### `polymarket_trader.py`
Client de trading réel utilisant py-clob-client :
- Authentification L1/L2 automatique
- Placement d'ordres avec vérification du solde
- Tracking des fills en temps réel
- Fermeture automatique de positions

```python
from polymarket_trader import PolymarketTrader

trader = PolymarketTrader()
balance = trader.get_balance()  # Solde USDC réel

# Placer un ordre
position = trader.place_market_order(
    token_id="0x123...",
    side="BUY",
    size=10.0
)
```

### `paper_trader.py`
Simulateur de trading sans risque :
- Solde virtuel configurable
- Fills simulés avec slippage réaliste
- Statistiques détaillées (Sharpe, win rate, etc.)
- Export JSON des résultats

```python
from paper_trader import PaperTrader

trader = PaperTrader(starting_balance=100.0)

# Trader comme en réel
position = trader.place_order("token", "BUY", 0.50, 10.0)
trader.close_position(position.position_id, 0.55, "Take Profit")

# Voir les stats
trader.display_statistics()
trader.export_results("my_results.json")
```

### `market_matcher.py`
Matching intelligent jeux ↔ marchés :
- Normalisation des noms d'équipes (50+ variations)
- Fuzzy matching avec score de confiance
- Identification automatique des outcomes
- Cache pour performance

```python
from market_matcher import MarketMatcher

matcher = MarketMatcher()

# Trouver le marché pour un jeu
market = matcher.match_game_to_market(nba_game, polymarket_markets)

# Trouver le token pour parier sur une équipe
token_id = matcher.get_token_id_for_team(market, "Lakers", bet_on_team=True)
```

### `optimizer.py`
Optimisation des paramètres par grid search :
- Test automatique de combinaisons
- Scoring composite (P&L, WR, Sharpe)
- Recommandations personnalisées
- Export des résultats

```bash
python optimizer.py
# Va tester 240 combinaisons et afficher les 10 meilleures
```

## 🎯 Stratégies de Trading (Inchangées)

1. **Fading Momentum Runs** : Parie contre les runs de 8+ points
2. **Fading Lead Changes** : Parie sur l'équipe qui perd le lead
3. **Close Game Advantage** : Home court au 4e quart
4. **Comeback Fading** : Fade les gros comebacks

## 📊 Nouveaux Métriques

Le bot V2 affiche maintenant :
- **Sharpe Ratio** : Ratio rendement/risque
- **Avg Win / Loss** : Gains et pertes moyens
- **Exposure** : Capital engagé
- **Available Balance** : Capital disponible
- **Win Rate** : % de trades gagnants
- **Total P&L** : Profit/Perte total

## ⚙️ Configuration Avancée

### Variables .env supplémentaires

```bash
# Trading Mode
PAPER_MODE=true              # true = paper, false = live

# Optimized Parameters (from optimizer.py)
MOMENTUM_RUN_THRESHOLD=10
LEAD_CHANGE_THRESHOLD=6
STOP_LOSS_PERCENTAGE=2.5
TAKE_PROFIT_PERCENTAGE=3.5
```

## 🧪 Workflow Recommandé

### Étape 1 : Paper Trading
```bash
# Tester pendant plusieurs jours
python bot_v2.py --paper --balance 100
```

Objectifs :
- ✅ Win rate > 55%
- ✅ Sharpe ratio > 1.0
- ✅ P&L positif sur 20+ trades

### Étape 2 : Optimisation
```bash
# Trouver les meilleurs paramètres
python optimizer.py
```

Mettre à jour `.env` avec les paramètres recommandés.

### Étape 3 : Plus de Paper Trading
```bash
# Re-tester avec paramètres optimisés
python bot_v2.py --paper
```

Confirmer l'amélioration des performances.

### Étape 4 : Live avec Petit Capital
```bash
# Commencer avec $20-50
python bot_v2.py --live
```

⚠️ **Surveillance constante requise**

## 🚨 Nouveaux Garde-Fous

### Paper Trading
- Slippage simulé (0.1% par défaut)
- Pas de risque financier
- Export automatique des résultats
- Statistiques complètes

### Live Trading
- Vérification du solde avant chaque ordre
- Confirmation des fills
- Retry avec backoff sur erreurs réseau
- Logs détaillés de chaque opération

## 📈 Résultats Paper Trading

Exemple de résultats après 1 session :

```
📄 PAPER TRADING RESULTS
============================================================
Starting Balance:     $100.00
Current Balance:      $112.50
Total P&L:            $12.50 (12.50%)
------------------------------------------------------------
Total Trades:         25
Win Rate:             64.0%
Avg Win:              $1.85
Avg Loss:             -$1.20
Sharpe Ratio:         1.45
------------------------------------------------------------
Open Positions:       0
Total Exposure:       $0.00
Available Balance:    $112.50
============================================================
```

## 🔄 Migration V1 → V2

Si vous utilisez déjà `bot.py` :

1. **Testez V2 en paper d'abord**
   ```bash
   python bot_v2.py --paper
   ```

2. **Comparez les performances**
   - V1 : Mock orders, pas de stats
   - V2 : Paper trading réaliste + analytics

3. **Passez au live quand prêt**
   ```bash
   python bot_v2.py --live
   ```

## 🛠️ Tests des Modules

```bash
# Tester le market matcher
python market_matcher.py

# Tester le paper trader
python paper_trader.py

# Tester le real trader (requiert .env configuré)
python polymarket_trader.py

# Tester l'optimizer
python optimizer.py
```

## 📚 Ressources

### Documentation
- [Polymarket CLOB API](https://docs.polymarket.com/)
- [py-clob-client GitHub]( https://github.com/Polymarket/py-clob-client)
- [BallDontLie NBA API](https://www.balldontlie.io/)

### Guides
- [Authentication Guide](https://docs.polymarket.com/developers/CLOB/authentication)
- [Polymarket Python Tutorial](https://www.polytrackhq.app/blog/polymarket-python-tutorial)

## ❓ FAQ

**Q: Dois-je utiliser le bot V1 ou V2 ?**
R: V2 est recommandé. Il a paper trading, meilleur matching, et analytics.

**Q: Paper trading est-il réaliste ?**
R: Oui, avec slippage simulé. Mais les fills réels peuvent varier.

**Q: Combien investir pour commencer en live ?**
R: $20-50 max pour débuter. Augmentez si profitable.

**Q: Le bot est-il profitable ?**
R: Pas garanti. Backtestez, optimisez, et testez en paper d'abord.

**Q: Puis-je trader 24/7 ?**
R: Oui, mais seulement quand il y a des matchs NBA en cours.

**Q: Comment arrêter le bot ?**
R: Ctrl+C pour shutdown gracieux (ferme toutes les positions).

## ⚠️ Disclaimers

- **Pas de garantie de profit** : Le trading comporte des risques
- **Testez d'abord** : Utilisez paper trading avant le live
- **Commencez petit** : $20-50 max pour débuter
- **Surveillez** : Gardez un œil sur le bot
- **À vos risques** : Vous êtes responsable de vos pertes

## 🤝 Contribution

Améliorations bienvenues :
- Ajout de sports (NFL, MLB)
- Nouveaux signaux de trading
- Amélioration du market matching
- Backtesting avec vraies données historiques

## 📄 License

Educational purposes only. Trade at your own risk.

---

**Made with 🏀 by AI**

**Version 2.0** | Dernière mise à jour : 2026-01-15
