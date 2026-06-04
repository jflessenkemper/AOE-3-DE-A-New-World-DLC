//==============================================================================
/* leader_revolution_support.xs

   Shared AI support layer for Fully Playable Revolutions civilizations.
   This is not a named leader personality; it keeps the merged revolution civs
   from behaving like generic fallback Europeans.
*/
//==============================================================================

bool gANWRevolutionSupportEnabled = false;

void anwInitRevolutionSupport(void)
{
   if (civIsRevolution() == false)
   {
      return;
   }

   gANWRevolutionSupportEnabled = true;
   cvMaxAge = cAge5;
   cvMaxArmyPop = 120;
   cvMaxCivPop = 80;
   cvOkToBuildForts = true;
   btBiasInf = 0.4;
   btBiasCav = 0.0;
   btBiasArt = 0.0;

   string rvltName = kbGetCivName(cMyCiv);

   if ((rvltName == "ANWAmericans") || (rvltName == "ANWMexicans") ||
       (rvltName == "ANWChileans") || (rvltName == "ANWColumbians") ||
       (rvltName == "ANWPeruvians") || (rvltName == "ANWBrazil") ||
       (rvltName == "ANWNapoleonicFrance"))
   {
      btBiasArt = 0.3;
   }

   if (rvltName == "ANWRevFrance")
   {
      btBiasInf = 0.6;
      btBiasArt = 0.0;
      btBiasCav = 0.0;
      btRushBoom = 0.2;
      btOffenseDefense = 0.4;
   }

   if ((rvltName == "ANWArgentines") || (rvltName == "ANWHungarians") ||
       (rvltName == "ANWTexians") || (rvltName == "ANWRioGrande") ||
       (rvltName == "ANWCalifornians"))
   {
      btBiasCav = 0.5;
      btBiasInf = 0.2;
   }

   if ((rvltName == "ANWCanadians") ||
       (rvltName == "ANWHaitians") || (rvltName == "ANWRomanians") ||
       (rvltName == "ANWEgyptians"))
   {
      btRushBoom = -0.2;
      btOffenseDefense = -0.2;
      cvMaxTowers = 6;
   }

   if ((rvltName == "ANWMayans") || (rvltName == "ANWYucatan") ||
       (rvltName == "ANWCentralAmericans") || (rvltName == "ANWPeruvians"))
   {
      btBiasNative = 0.6;
      btBiasTrade = 0.2;
   }

   anwLogLeaderState("revolution support initialized for " + rvltName);
   // Boot-time heartbeat probe — matches the pattern in every named leader
   // file (`anwProbe("meta.leader_init", "leader=<name>")`). Without this the
   // hub-test + compliance probe scrapers can't tell whether the support
   // layer ever ran for a given revolution civ.
   anwProbe("meta.leader_init", "leader=revolution_support rvlt=" + rvltName);
}

rule anwRevolutionArmyProfile
inactive
minInterval 60
{
   anwLogRuleTick("anwRevolutionArmyProfile");
   if (gANWRevolutionSupportEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() >= cAge3)
   {
      cvMaxArmyPop = 130;
   }

   if (kbGetAge() >= cAge4)
   {
      cvMaxArmyPop = 145;
      btBiasInf = btBiasInf + 0.1;
      btBiasArt = btBiasArt + 0.1;
   }

   if (btBiasInf > 1.0)
   {
      btBiasInf = 1.0;
   }
   if (btBiasArt > 1.0)
   {
      btBiasArt = 1.0;
   }
}

void anwEnableRevolutionSupportRules(void)
{
   if (gANWRevolutionSupportEnabled == false)
   {
      return;
   }

   xsEnableRule("anwRevolutionArmyProfile");
}
