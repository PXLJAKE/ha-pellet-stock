# Häufige Fragen

## Funktioniert es mit meinem Kessel?

Ja, wenn deine Heizung eines davon in Home Assistant hat: einen kg-Zähler, einen kWh-Zähler, eine Ein/Aus-Entität für den Brenner oder einen Betriebsstundenzähler. Die Integration spricht nicht selbst mit dem Kessel, deshalb ist der Hersteller egal.

## Mein Sensor springt jeden Tag auf null. Ist das ein Problem?

Nein. Ein Tageszähler, der um Mitternacht zurückspringt, wird erkannt, auch wenn Home Assistant die Null um Mitternacht verpasst.

## Mein Kessel zeigt schon einen Bestand. Soll ich diesen Sensor einbinden?

Trag seinen Wert einmal als aktuellen Bestand ein. Ein Bestand, den der Kessel selbst berechnet, kommt aus demselben Verbrauch. Als Füllstandssensor bringt er deshalb nichts. Die Füllstands-Option ist für echte Messungen wie Waage, Ultraschall oder Radar.

## Ich trage Lieferungen auch am Kessel ein. Stört das?

Nein. Die Integration liest nur den Verbrauch. Eine Lieferung, die du am Kessel einträgst, ändert diesen Wert nicht.

## Kann ich meinen alten Verbrauch in die Diagramme bekommen?

Ja, wenn die Quelle ein Sensor mit Langzeitstatistik ist. Siehe [So funktioniert die Übernahme des Verlaufs](configuration.md#so-funktioniert-die-ubernahme-des-verlaufs).

## Wie wird die Reichweite berechnet?

Bestand geteilt durch den Durchschnittsverbrauch der letzten 14 vollen Tage. Das Attribut `reason` des Sensors *Reichweite* zeigt die Zahlen.

## Wie wird der Preis berechnet?

Als gleitender Durchschnitt. Eine Lieferung mischt sich mit dem Rest im Lager: Wert des Rests plus Wert der Lieferung, geteilt durch den neuen Bestand.

## Kann ich mehrere Lager haben?

Ja. Jedes Lager ist ein eigener Eintrag mit eigenem Gerät, eigenen Entitäten und eigener Karte.

## Braucht es das Internet?

Nein. Alle Daten bleiben in Home Assistant.

## Welche Sprachen gibt es?

Deutsch und Englisch. Die Karte folgt der Sprache von Home Assistant.
