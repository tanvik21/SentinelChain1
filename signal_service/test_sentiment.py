import sys
sys.stdout.reconfigure(encoding='utf-8')
from ml.sentiment_signal import SentimentSignalEngine

e = SentimentSignalEngine()
signals = e.run_sentiment_scan()

print(f"\nSignals found: {len(signals)}")
print("-" * 70)
for s in signals:
    print(f"  [{s['severity']}] {s['threat_type']}: score={s['threat_score']:.2f}")
    print(f"       {s['headline'][:70]}")
    print(f"       -> {s['summary'][:70]}")
    print()

print("\nCorridor Sentiment Scores:")
for c in ['NH48','NH44','NH47','NH19','NH16','NH27']:
    score = e.get_corridor_sentiment_score(c)
    bar = "#" * int(score * 30)
    print(f"  {c}: {bar} {score:.3f}")

print("\nCommodity Sentiment Scores:")
for com in ['agri','textile','pharma','auto_parts','electronics']:
    score = e.get_commodity_sentiment_score(com)
    bar = "#" * int(score * 30)
    print(f"  {com:<12}: {bar} {score:.3f}")
