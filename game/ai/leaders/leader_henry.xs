//==============================================================================
/* leader_henry.xs

   Infante Dom Henrique de Avis - Prince Henry the Navigator, founder of
   the Portuguese age of exploration personality.

   Historical doctrine:
     - Carrack and caravel program: Sagres-trained crews opened the
       African coast and the Atlantic. Mapped to a strong navy preference
       (cvOkToTrainNavy) and a high Trade Route bias - the empire is
       maritime trade.
     - Town Centre wagons (Portuguese civ unique): each shipment includes
       a free TC, encouraging sprawling commerce-first expansion. Mapped
       to the Distributed Economic Network style.
     - Cassador / Crossbow / Musketeer composition: Portuguese line
       infantry was professional but never the centerpiece. Mapped to a
       moderate infantry bias and a real artillery share for the
       Organ Gun signature unit.
     - Padrao stones and overseas garrisons: small forward fort lines
       defending trade hubs, not large standing armies. Mapped to the
       forward base style from Fortress on.
     - Order of Christ patronage: religious-military hybrid funded the
       voyages. Mapped to a slight Native Treaty lean for Indian Ocean
       allies.
*/
//==============================================================================

bool gHenryRulesEnabled = false;

void initLeaderHenry(void)
{
   llVerboseEcho("A New World: activating Prince Henry the Navigator personality.");

   llSetBalancedPersonality();
   btRushBoom = -0.4;             // Hard boom; the carracks fund the war.
   btOffenseDefense = -0.05;
   btBiasTrade = 0.6;             // Maritime empire.
   btBiasNative = 0.15;
   llSetMilitaryFocus(0.55, 0.15, 0.4);

   // LL-BUILD-STYLE-BEGIN
   llUseNavalMercantileCompoundStyle(2);
   gLLEconomicDistanceMultiplier = 1.30;
   // LL-BUILD-STYLE-END
   llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);

   cvOkToBuildForts = true;
   cvOkToTrainNavy = true;
   cvMaxTowers = 5;
   cvMaxArmyPop = 110;

   gHenryRulesEnabled = true;
   llLogLeaderState("Henry initialized");
   llProbe("meta.leader_init", "leader=henry");
}

//------------------------------------------------------------------------------
// Discovery: Sagres expansion. Town Centre wagons placed wide, Settler
// push, Trade Route prioritized.
//------------------------------------------------------------------------------
rule henrySagresExpansion
inactive
minInterval 60
{
   llLogRuleTick("henrySagresExpansion");
   if (gHenryRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.6;
      btBiasTrade = 0.75;
      cvMinNumVills = 18;
   }
}

//------------------------------------------------------------------------------
// Colonial: Cassador screen. Cassador skirmishers and Crossbowman screen
// behind a sprawling Town Centre web; light raids only.
//------------------------------------------------------------------------------
rule henryCassadorScreen
inactive
minInterval 50
{
   llLogRuleTick("henryCassadorScreen");
   if (gHenryRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = -0.2;
      btOffenseDefense = 0.15;
      btBiasInf = 0.7;
      btBiasCav = 0.15;
      btBiasArt = -0.15;
      cvMinNumVills = 32;
   }
}

//------------------------------------------------------------------------------
// Fortress: Overseas Empire. Organ Gun appears, Cassador mass forms,
// Dragoon counter-cavalry; padrao fort line locks down trade hubs.
//------------------------------------------------------------------------------
rule henryOverseasEmpire
inactive
minInterval 55
{
   llLogRuleTick("henryOverseasEmpire");
   if (gHenryRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.4;
      btBiasInf = 0.85;
      btBiasCav = 0.4;
      btBiasArt = 0.6;             // Organ Gun signature share.
      btBiasTrade = 0.7;
      cvMaxArmyPop = 125;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Industrial: Carrack empire at scale. Heavy Cannon and Organ Gun park,
// Cassador / Musketeer mass; trade fleet underwrites the war.
//------------------------------------------------------------------------------
rule henryCarrackEmpire
inactive
minInterval 70
{
   llLogRuleTick("henryCarrackEmpire");
   if (gHenryRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.6;
      btBiasInf = 0.95;
      btBiasCav = 0.5;
      btBiasArt = 0.75;
      btBiasTrade = 0.7;
      cvMaxArmyPop = 140;
      llEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Lusitanian supremacy - maximum Cassador / Musketeer / Heavy
// Cannon mass with continuous Organ Gun fire and full overseas trade.
//------------------------------------------------------------------------------
rule henryLusitanianSupremacy
inactive
minInterval 90
{
   llLogRuleTick("henryLusitanianSupremacy");
   if (gHenryRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.75;
      btBiasInf = 1.0;
      btBiasCav = 0.55;
      btBiasArt = 0.85;
      btBiasTrade = 0.8;
      cvMaxArmyPop = 155;
   }
}

void enableLeaderHenryRules(void)
{
   if (gHenryRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("henrySagresExpansion");
   xsEnableRule("henryCassadorScreen");
   xsEnableRule("henryOverseasEmpire");
   xsEnableRule("henryCarrackEmpire");
   xsEnableRule("henryLusitanianSupremacy");
}
