//==============================================================================
/* leader_napoleon.xs

   Napoleon Bonaparte - Emperor of the French, Grande Armée commander,
   master of operational art personality.

   Historical doctrine:
     - Grande Armée corps system (1805 onward): Napoleon fought with
       self-contained corps that could fix the enemy until the rest of the
       army concentrated. Mapped to a hyper-aggressive Forward Operational
       Line build with strong forward base posture from Colonial.
     - Grand Battery doctrine (Friedland 1807, Wagram 1809, Borodino 1812):
       Senarmont and Drouot pioneered massed artillery as the decisive
       arm. Mapped to the highest artillery weight of any revolution and
       a deep Heavy Cannon park from Fortress on.
     - Imperial Guard infantry (Garde Impériale): line-of-the-line elite
       infantry held in reserve until decisive moment. Mapped to a
       Musketeer / Grenadier mass commitment from Fortress on.
     - Cuirassier shock cavalry (Murat, Kellermann, Nansouty): heavy
       cavalry as the breakthrough hammer. Mapped to a real Cuirassier /
       Hussar weight that supports rather than leads the artillery.
     - Continental System (Berlin Decree 1806): trade with Britain
       refused. Mapped to a hard negative trade bias and zero native
       treaty leaning. The Republic conscripts and the Emperor commands.
*/
//==============================================================================

bool gNapoleonRulesEnabled = false;

void initLeaderNapoleon(void)
{
   anwVerboseEcho("A New World: activating Napoleon Bonaparte personality.");

   anwSetAggressivePersonality();
   btRushBoom = 0.1;              // Light boom; the campaign opens fast.
   btOffenseDefense = 0.85;
   btBiasTrade = -0.4;            // Continental System.
   btBiasNative = -0.4;           // No foreign auxiliaries.
   anwSetMilitaryFocus(0.6, 0.4, 0.85);  // Artillery dominant.

   // LL-BUILD-STYLE-BEGIN
   anwUseForwardOperationalLineStyle(2);
   gANWMilitaryDistanceMultiplier = 0.85;
   anwSetBuildStrongpointProfile(2, 2, 3, true);
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.6, 0.4, 1, 3.0);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 125;
   cvDefenseReflexRadiusActive = 80.0;
   cvDefenseReflexSearchRadius = 80.0;
   cvDefenseReflexRadiusPassive = 28.0;

   gNapoleonRulesEnabled = true;
   anwLogLeaderState("Napoleon initialized");
   anwProbe("meta.leader_init", "leader=napoleon");
}

//------------------------------------------------------------------------------
// Discovery: Convention assembly. Settler push under Continental System
// trade refusal; the Republic conscripts before it fights.
//------------------------------------------------------------------------------
rule napoleonConventionAssembly
inactive
minInterval 60
{
   anwLogRuleTick("napoleonConventionAssembly");
   if (gNapoleonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.1;
      btBiasTrade = -0.4;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Italian campaign tempo. Musketeer mass with light Hussar
// screen, Field Gun trickle. Forward base immediately.
//------------------------------------------------------------------------------
rule napoleonItalianCampaign
inactive
minInterval 50
{
   anwLogRuleTick("napoleonItalianCampaign");
   if (gNapoleonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.1;
      btOffenseDefense = 0.85;
      btBiasInf = 0.85;
      btBiasCav = 0.45;
      btBiasArt = 0.5;
      btBiasTrade = -0.6;          // Continental System hardens.
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Grand Battery. Massed Field Gun park, Musketeer / Grenadier
// mass, Cuirassier shock reserve. The Friedland signature.
//------------------------------------------------------------------------------
rule napoleonGrandBattery
inactive
minInterval 55
{
   anwLogRuleTick("napoleonGrandBattery");
   if (gNapoleonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.9;
      btBiasInf = 0.9;
      btBiasCav = 0.6;             // Cuirassier reserve.
      btBiasArt = 0.9;             // Grand Battery as decisive arm.
      cvMaxArmyPop = 140;
   }
}

//------------------------------------------------------------------------------
// Industrial: Wagram doctrine. Heavy Cannon park, Imperial Guard mass,
// Cuirassier wing. The corps system at full operational tempo.
//------------------------------------------------------------------------------
rule napoleonWagramDoctrine
inactive
minInterval 70
{
   anwLogRuleTick("napoleonWagramDoctrine");
   if (gNapoleonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.7;
      btBiasArt = 0.95;
      cvMaxArmyPop = 160;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Empire at war - maximum Musketeer / Grenadier / Heavy Cannon
// mass with Cuirassier wing; the Grande Armée at full pop.
//------------------------------------------------------------------------------
rule napoleonImperialTempo
inactive
minInterval 90
{
   anwLogRuleTick("napoleonImperialTempo");
   if (gNapoleonRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 1.0;
      btBiasInf = 1.0;
      btBiasCav = 0.75;
      btBiasArt = 1.0;
      cvMaxArmyPop = 180;
      anwEnableForwardBaseStyle();
   }
}

void enableLeaderNapoleonRules(void)
{
   if (gNapoleonRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("napoleonConventionAssembly");
   xsEnableRule("napoleonItalianCampaign");
   xsEnableRule("napoleonGrandBattery");
   xsEnableRule("napoleonWagramDoctrine");
   xsEnableRule("napoleonImperialTempo");
}
