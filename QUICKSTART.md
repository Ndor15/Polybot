# 🚀 Quick Start Guide - NBA Polymarket Bot

Guide rapide pour lancer le bot en 5 minutes.

## ⚡ Installation Express

```bash
# 1. Cloner
git clone <repo-url>
cd Polybot

# 2. Installer
pip install -r requirements.txt

# 3. Lancer en mode paper (aucune config requise)
python bot_v2.py --paper
```

**C'est tout !** Le bot va commencer à trader avec $100 virtuels dès qu'un match NBA est en cours.

## 📋 Prérequis

- Python 3.8+
- Internet pour APIs NBA et Polymarket
- Aucune clé API nécessaire pour mode paper

## 🎮 Modes de Lancement

### Mode 1: Paper Trading (Recommandé)
Trading simulé, zéro risque, parfait pour apprendre.

```bash
# Balance par défaut ($100)
python bot_v2.py --paper

# Balance custom
python bot_v2.py --paper --balance 500
```

**Quand utiliser** : Toujours en premier ! Pour tester stratégies et paramètres.

### Mode 2: Live Trading (Experts)
Trading réel avec vraie argent. Nécessite configuration.

```bash
# Setup d'abord
cp .env.example .env
# Éditer .env et ajouter POLYMARKET_PRIVATE_KEY

# Puis lancer
python bot_v2.py --live
```

**Quand utiliser** : Seulement après avoir été profitable en mode paper sur 50+ trades.

## 🔧 Configuration Minimale

### Pour Paper Trading
Aucune configuration nécessaire ! Ça marche out of the box.

### Pour Live Trading
Un seul paramètre requis dans `.env` :

```bash
POLYMARKET_PRIVATE_KEY=votre_clé_privée_polygon_wallet
```

## 📊 Voir les Résultats

Le bot affiche les stats toutes les 10 itérations :

```
📄 PAPER TRADING RESULTS
Starting Balance:     $100.00
Current Balance:      $108.50
Total P&L:            $8.50 (8.50%)
Total Trades:         12
Win Rate:             66.7%
```

Les résultats complets sont exportés automatiquement en JSON à l'arrêt.

## ⏹️ Arrêter le Bot

**Ctrl+C** : Arrêt gracieux
- Ferme toutes les positions
- Affiche les stats finales
- Exporte les résultats

## 📈 Prochaines Étapes

Après quelques sessions en paper :

1. **Optimiser les paramètres**
   ```bash
   python optimizer.py
   ```

2. **Mettre à jour .env** avec les paramètres recommandés

3. **Re-tester en paper** avec nouveaux paramètres

4. **Passer en live** quand profitable

## 🎯 Stratégies du Bot

Le bot trade automatiquement sur 4 signaux :

1. **Momentum Runs** : Équipe fait un run → parie CONTRE (fade)
2. **Lead Changes** : Lead change → parie sur perdant (contrarian)
3. **Close Games** : Match serré 4Q → léger edge home
4. **Comebacks** : Gros comeback → fade le momentum

## ⚙️ Ajuster les Paramètres

Éditer `.env` pour changer les seuils :

```bash
# Sensibilité des signaux
MOMENTUM_RUN_THRESHOLD=8     # Points pour déclencher signal
LEAD_CHANGE_THRESHOLD=5      # Swing de points minimum

# Gestion du risque
STOP_LOSS_PERCENTAGE=2.5     # Stop à -2.5%
TAKE_PROFIT_PERCENTAGE=3.0   # TP à +3.0%
MAX_CONCURRENT_TRADES=3      # Max 3 positions simultanées

# Taille des trades
TRADE_SIZE_USDC=5.0          # $5 par trade
```

## 🔍 Tester les Modules

Chaque module peut être testé individuellement :

```bash
# Tester le paper trader
python paper_trader.py

# Tester le market matcher
python market_matcher.py

# Tester l'optimizer
python optimizer.py
```

## ❓ FAQ Express

**Q: Ça marche tout le temps ?**
R: Non, seulement quand il y a des matchs NBA en cours (vérifier sur NBA.com).

**Q: C'est rentable ?**
R: Pas garanti. C'est pour ça qu'on teste en paper d'abord.

**Q: Combien investir en live ?**
R: $20-50 max pour débuter. Augmentez si profitable.

**Q: Je peux laisser tourner H24 ?**
R: Oui mais surveillez. Bugs possibles.

**Q: Où sont les logs ?**
R: Fichier `nba_polymarket_bot.log` dans le répertoire.

## 🚨 Points d'Attention

### ✅ À Faire
- Tester en paper d'abord (minimum 20-30 trades)
- Vérifier win rate > 55% avant live
- Commencer avec petit capital en live
- Surveiller le bot régulièrement
- Exporter et analyser les résultats

### ❌ À Éviter
- Passer en live sans tester en paper
- Investir plus que vous pouvez perdre
- Laisser tourner sans surveillance
- Ignorer les stop loss
- Trader sur des marchés à faible liquidité

## 📚 Ressources

- **README_V2.md** : Documentation complète
- **README.md** : Documentation version 1
- **optimizer.py** : Optimisation automatique
- [Polymarket Docs](https://docs.polymarket.com/)

## 🆘 Problèmes Courants

### "No live games"
**Solution** : Attendre qu'un match NBA commence. Vérifier sur NBA.com.

### "py-clob-client not installed" (mode live)
**Solution** : `pip install py-clob-client`

### "POLYMARKET_PRIVATE_KEY not set" (mode live)
**Solution** : Configurer .env avec votre clé wallet Polygon

### Bot ne trade pas
**Solution** :
- Vérifier que matchs NBA sont en cours
- Vérifier logs pour voir les signaux générés
- Baisser MIN_CONFIDENCE dans .env

## 💡 Conseils Pro

1. **Laissez tourner 1-2 semaines en paper** avant le live
2. **Notez les patterns** : quels signaux sont plus profitables ?
3. **Optimisez régulièrement** avec optimizer.py
4. **Commencez petit** en live : $20-50
5. **Scale progressivement** si profitable

## 🎓 Workflow Idéal

```
1. Paper trading (1-2 semaines)
   ↓
2. Analyser résultats
   ↓
3. Optimiser paramètres
   ↓
4. Re-tester en paper
   ↓
5. Live avec $20-50
   ↓
6. Scale si profitable
```

---

**Prêt à commencer ?**

```bash
python bot_v2.py --paper
```

Bon trading ! 🏀💰

*Note: Ce bot est éducatif. Trade at your own risk.*
