# Noch zu erledigen

    - Sounds einbinden
    - Heat-API:
        - Objekte zuordnen
        - UserIDs zuordnen -> Rausfinden wie ich ein bekannter User werde
        -> top = y
        -> left = x
            -> "icon1": {"x": 300, "y": 400, "width": 60, "height": 60}
    - Bei Follow -> Hub triggern

    - Sonderzeichen drucken
        - ┻━┻ ︵ ¯\(ツ)/¯ ︵ ┻━┻
        - ¯\(◉◡◔)/¯
        - __̴ı̴̴̡ ̡͌l̡̡̡ ̡͌l̡*̡̡ ̴̡ı̴̴̡ ̡̡͡|̲̲͡ ̲▫̲͡ ̲̲͡π̲̲͡ ̲̲͡▫̲̲͡ ̲|̡̡̡ ̡ ̴̡ı̴̡̡ ̡͌l̡̡̡.___

        - Bild statt Text drucken bei !print


# Ideen zum umsetzen

    - Clicking a hidden Easter Egg could show a special message on stream
    - 🕹️ 4. Twitch Mini-Games in the Overlay
        🎮 Feature: Viewers Play Interactive Games Directly on Screen
        ✅ Example Ideas:

        A click-based game where viewers collect resources 🏆
        A "Battle Royale" mode, where viewers fight with commands 🥊
        A puzzle challenge, where clicking icons completes a sequence
        💡 How to Implement
        Use the Heat API to detect clicks for real-time input
        Store progress in Firebot or FastAPI
        Trigger animations based on game mechanics
    - 💾 7. Persistent Overlay (Save & Load State)
        🔄 Feature: Overlay Remembers Viewer Interactions
        ✅ Example Ideas:

        Planets persist across streams 🌍
        Leaderboard for most clicks is saved & displayed 🔥
        Secret achievements unlock special overlay effects
        💡 How to Implement
        Store data in a SQLite or Firebot database
        Load stored data when the overlay refreshes
        Sync between FastAPI & the overlay via WebSockets
