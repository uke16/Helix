Problem: consultant chat session via open webui hat keine history. Jeder chat ist neue Session. Das soll nicht so sein.
  
## **Session History**
Zum **Open WebUI Session Problem** - jeder Chat ist eine neue Session:
Das liegt daran, dass der `SessionManager` die Session-ID aus:
1.  Hash der ersten Nachricht
    
2.  **Timestamp** (!)
    
generiert. Der Timestamp ändert sich bei jedem Request.
**Fix-Vorschlag für das nächste ADR:**
Open WebUI sendet einen `X-Conversation-ID` Header. Dieser sollte für die Session-Zuordnung verwendet werden statt des Timestamps.
kannst du dafür auch ein ADR erstellen und speichern?