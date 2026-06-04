//==============================================================================
/* leader_hidalgo.xs

   Miguel Gregorio Antonio Ignacio Hidalgo y Costilla - "Padre de la
   Patria", Mexican War of Independence personality.

   Historical doctrine:
     - Grito de Dolores (1810): Hidalgo raised a peasant army of 80,000+
       within weeks. Mapped to a fast Colonial mass-infantry commitment
       and a strong Native Treaty leaning (indigenous and mestizo levies).
     - Insurgente irregular tactics: machete columns and improvised
       artillery, not professional drilled lines. Mapped to a strong
       infantry bias and a real but supporting artillery share.
     - Soldadera support: women followed and supplied the army on march -
       the civ's hacienda / mission economy plays a similar role. Mapped
       to a moderate Trade Route lean rather than zero.
     - Independencia federalism: regional caudillos build local forces.
       Mapped to a Distributed Economic Network style.
     - Insurgente, Soldado, Chinaco lancer, Salteador raider, Granadero
       grenadier - the Mexican standard composition is recognizable.
*/
//==============================================================================

bool gHidalgoRulesEnabled = false;

void initLeaderHidalgo(void)
{
   anwVerboseEcho("A New World: activating Miguel Hidalgo personality.");

   anwSetAggressivePersonality();
   btRushBoom = 0.05;             // Light boom; the Grito comes early.
   btOffenseDefense = 0.65;
   btBiasTrade = 0.1;
   btBiasNative = 0.45;           // Indigenous and mestizo levies.
   anwSetMilitaryFocus(0.7, 0.3, 0.25);

   // LL-BUILD-STYLE-BEGIN
   anwUseRepublicanLeveeStyle(1);
   gANWEconomicDistanceMultiplier = 1.15;
   anwSetBuildStrongpointProfile(2, 1, 2, false);
   // LL-BUILD-STYLE-END
   anwSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);

   cvOkToBuildForts = true;
   cvMaxTowers = 4;
   cvMaxArmyPop = 120;            // Levée-en-masse is large.

   gHidalgoRulesEnabled = true;
   anwLogLeaderState("Hidalgo initialized");
   anwProbe("meta.leader_init", "leader=hidalgo");
}

//------------------------------------------------------------------------------
// Discovery: Hacienda assembly. Settler push and Mission placement;
// village priests organize the muster.
//------------------------------------------------------------------------------
rule hidalgoHaciendaAssembly
inactive
minInterval 60
{
   anwLogRuleTick("hidalgoHaciendaAssembly");
   if (gHidalgoRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() <= cAge1)
   {
      btRushBoom = -0.15;
      btBiasNative = 0.6;
      cvMinNumVills = 16;
   }
}

//------------------------------------------------------------------------------
// Colonial: Insurgente surge. Insurgente militia and Soldado pressure on
// enemy villager and trade lines, Salteador raider screen.
//------------------------------------------------------------------------------
rule hidalgoInsurgenteSurge
inactive
minInterval 50
{
   anwLogRuleTick("hidalgoInsurgenteSurge");
   if (gHidalgoRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge2)
   {
      btRushBoom = 0.0;
      btOffenseDefense = 0.75;
      btBiasInf = 0.9;
      btBiasCav = 0.3;
      btBiasArt = -0.3;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Fortress: Insurgent Momentum. Granadero shock, Chinaco lancers, Soldado
// musket mass; the levée army takes the field.
//------------------------------------------------------------------------------
rule hidalgoInsurgentMomentum
inactive
minInterval 55
{
   anwLogRuleTick("hidalgoInsurgentMomentum");
   if (gHidalgoRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge3)
   {
      btOffenseDefense = 0.8;
      btBiasInf = 0.95;
      btBiasCav = 0.55;
      btBiasArt = 0.35;
      cvMaxArmyPop = 135;
   }
}

//------------------------------------------------------------------------------
// Industrial: Independencia campaign. Heavy Cannon and Mortar share rises;
// Soldado / Chinaco mass at scale. The Republic takes shape.
//------------------------------------------------------------------------------
rule hidalgoIndependenciaCampaign
inactive
minInterval 70
{
   anwLogRuleTick("hidalgoIndependenciaCampaign");
   if (gHidalgoRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() == cAge4)
   {
      btOffenseDefense = 0.85;
      btBiasInf = 1.0;
      btBiasCav = 0.65;
      btBiasArt = 0.6;
      cvMaxArmyPop = 150;
      anwEnableForwardBaseStyle();
   }
}

//------------------------------------------------------------------------------
// Imperial: Mexican Republic at arms - maximum Soldado / Granadero /
// Chinaco / Heavy Cannon mass with native confederation pulled tight.
//------------------------------------------------------------------------------
rule hidalgoRepublicAtArms
inactive
minInterval 90
{
   anwLogRuleTick("hidalgoRepublicAtArms");
   if (gHidalgoRulesEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge5)
   {
      btOffenseDefense = 0.95;
      btBiasInf = 1.0;
      btBiasCav = 0.7;
      btBiasArt = 0.75;
      btBiasNative = 0.65;
      cvMaxArmyPop = 165;
   }
}

void enableLeaderHidalgoRules(void)
{
   if (gHidalgoRulesEnabled == false)
   {
      return;
   }

   xsEnableRule("hidalgoHaciendaAssembly");
   xsEnableRule("hidalgoInsurgenteSurge");
   xsEnableRule("hidalgoInsurgentMomentum");
   xsEnableRule("hidalgoIndependenciaCampaign");
   xsEnableRule("hidalgoRepublicAtArms");
}
