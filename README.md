# smarthome.plugin.meter
Meter plugin for smarthome.py


## Konfiguration

###1. Plugin aktivieren
Eintrag für das Plugin in der plugin.conf anlegen:

  [meter]
    class_name = Meter
    class_path = plugins.meter
      
Über zusätzliche Parameter kann das Datums- und Zeitformat festgelegt werden.
    
    dateformat = %d.%m.%Y
    timeformat = %H:%M:%S
  
    
Attribut | Bedeutung | Standardwert
-------- | --------- | -----
dateformat | Standardformat für Datumsangaben (siehe strftime) | %d.%m.%Y
timeformat | Standardformat für Zeitangaben (siehe strftime) | %H:%M:%S

###2. "Tick"-Item anlegen
Das Tick-Item muss bei jedem Impuls des Zählers __UMGESCHALTET__ werden! (Binäreingang/Tasterschnittstelle auf "UM" bei steigender Flanke, "Keine Reaktion" bei fallender Flanke stellen)

  [stromzaehler]
    [[tick]]
      type = bool
      knx_dpt = 1
      knx_listen = 0/0/1
      
###3. "Power"-Item anlegen
Die aktuelle Leistung wird auf Basis der Zeit zwischen den letzten beiden Ticks berechnet und im "Power"-Item abgelegt

  [stromzaehler]
    [[power]]
      type = num
      sqlite = yes

###4. "Zähler"-Item anlegen

  [stromzaehler]
    [[zaehler]]
      type = num
      sqlite = yes
      meter_tick = stromzaehler.tick
      meter_increment = 0.001
      meter_power = stromzaehler.power
      
Attribut | Bedeutung
-------- | ---------
type | Datentyp. Sollte immer "num" sein
sqlite | Muss auf "yes" gesetzt sein, damit Auswertungen auf den Zählerstand gemacht werden können. Wenn keine Auswertungen gemacht werden sollen, kann das Attribut entfallen
meter_tick | "Tick"-Item, dass den Zählerstand erhöht
meter_increment | Wert, um den der Zählerstand bei jedem "Tick" erhöht wird
meter_power | "Power"-Item, in dass die aktuelle Leistung berechnet wird
  
  
## Auswertungen
Über das Plugin können einfach Auswertungen (Verbrauch am Vortag, in der Vorwoche, etc) ermittelt werden. Das Plugin stellt dazu eine Methode bereit, die über `eval` eingebunden werden kann:

  sh.meter.get_usage([Zähleritem], [Startpunkt], [Länge], [Item für Startdatum], [Item für Enddatum])

Parameter | Bedeutung
-------- | ---------
[Zähleritem] | Id des "Zähler"-Items, über das die Auswertung gemacht werden soll
[Startpunkt] | Wie weit soll der Startpunkt in der Vergangenheit liegen. Format ist #[d|w|m|y], d=Tage, w=Wochen (á 7 Tage), m=Monate (á 30 Tage), y=Jahre(á 365 Tage). z. B. 1d= 1 Tag, 2w=2 Wochen
[Länge] | Welcher Zeitraum soll betrachtet werden. Format wie bei [Startpunkt]
[Item für Startdatum] | Optionaler Parameter: Das berechnete Startdatum des Zeitraums wird in dieses Item geschrieben, wenn es angegeben ist
[Item für Enddatum] | Optionaler Parameter: Das berechnete Enddatum des Zeitraums wird in dieses Item geschrieben, wenn es angegeben ist

Zeiträume werden immer als ganze Tage berechnet (00:00:00 Uhr bis 23:59:59 Uhr)!

###Verwendung im Item

  [stromzaehler]
    [[gestern]]
      type = num
      enforce_updates = yes
      eval = sh.meter.get_usage("stromzaehler.zaehler", "1d", "1d", "stromzaehler.gestern.start", "stromzaehler.gestern.ende")
      crontab = init = 1 | 0 0 * * = 1
      [[[start]]]
        type = str
      [[[ende]]]
        type= str

				
