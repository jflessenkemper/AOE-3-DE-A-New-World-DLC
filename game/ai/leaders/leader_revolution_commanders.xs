//==============================================================================
/* leader_revolution_commanders.xs

   Bespoke commander personalities for the playable Revolution roster.

   Each civ gets a unique historical doctrine assigned in
   anwInitRevolutionCommander() and a bespoke per-age treatment
   applied through five rules below (Discovery -> Imperial). Civs with
   their own dedicated leader files (Napoleonic France, Americans,
   Mexicans -> Washington / Hidalgo / Napoleon) skip this dispatch.

   Civ ID legend (gRvltCivId):
       1  Canadians          - Isaac Brock, infantry-fort frontier
       2  RevolutionaryFrance- Robespierre, levee-en-masse conscription
       4  Brazil             - Pedro I, Imperial line + Hessian mercenary
       5  Argentines         - San Martin, Granadero shock cavalry
       6  Chileans           - O'Higgins, balanced Republican infantry
       7  Peruvians          - Santa Cruz, Andean fort line + native levy
       8  Columbians         - Bolivar, Llanero light cavalry sweeps
       9  Haitians           - Toussaint, mass infantry insurrection
      10  Indonesians        - Diponegoro, Java War guerrilla / fort
      11  SouthAfricans      - Kruger, Boer commando trader-cavalry
      12  Finnish            - Mannerheim, Mannerheim-line ski infantry
      13  Hungarians         - Kossuth, Honved hussar + line uprising
      14  Romanians          - Cuza, Danubian principalities consolidation
      15  Barbary            - Barbarossa, corsair raider economy
      16  Egyptians          - Muhammad Ali, Nizam-i Cedid modernization
      17  CentralAmericans   - Morazan, Federal Republic native muster
      18  BajaCalifornians   - Alvarado, Californio horse raid
      19  Yucatan            - Carrillo Puerto, Maya levy uprising
      20  RioGrande          - Canales, Rio Grande Republic horse
      21  Mayans             - Canek, indigenous insurrection mass
      22  Californians       - Vallejo, ranchero defense + trade
      23  Texians            - Houston, Republic of Texas militia
*/
//==============================================================================

bool gANWRevolutionCommanderEnabled = false;
int gRvltCivId = 0;

void anwInitRevolutionCommander(void)
{
   if (civIsRevolution() == false)
   {
      return;
   }

   string rvltName = kbGetCivName(cMyCiv);

   // ANWAmericans is handled exclusively by its dedicated leader file
   // (initLeaderWashington) and has no branch below, so it must early-return.
   //
   // ANWMexicans and ANWNapoleonicFrance are dispatched to their dedicated
   // files (initLeaderHidalgo / initLeaderNapoleon) in aiLoaderStandard.xs
   // ONLY when the base civ id matches (cCivDEMexicans / civ-name match). The
   // ANW-prefixed *revolution* tokens fall through that gate to here, so they
   // MUST run their explicit branches below — early-returning for them left
   // gANWWallStrategy at the FortressRing default and never applied the Hidalgo
   // levee / Napoleon operational-line doctrine (caught by xs_sim_doctrine).
   if (rvltName == "ANWAmericans")
   {
      return;
   }

   // Default before the per-civ override.
   anwSetBalancedPersonality();
   gRvltCivId = 0;

   // ── ANW revolution civs (24–42) ───────────────────────────────────────────
   if (rvltName == "ANWArgentines")
   {
      anwVerboseEcho("A New World: activating ANW Argentina San Martin personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.15;
      btBiasNative = 0.1;
      anwSetMilitaryFocus(0.4, 0.85, 0.2);
      // LL-BUILD-STYLE-BEGIN
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.85;
      anwSetBuildStrongpointProfile(1, 2, 3, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 3;
      cvMaxArmyPop = 115;
      gRvltCivId = 24;
   }
   else if (rvltName == "ANWBarbary")
   {
      anwVerboseEcho("A New World: activating ANW Barbary Barbarossa personality.");
      anwSetBalancedPersonality();
      btRushBoom = 0.0;
      btOffenseDefense = 0.55;
      btBiasTrade = 0.5;
      btBiasNative = 0.25;
      anwSetMilitaryFocus(0.4, 0.65, 0.2);
      // LL-BUILD-STYLE-BEGIN
      anwUseNavalMercantileCompoundStyle(2);
      gANWEconomicDistanceMultiplier = 1.20;
      anwSetBuildStrongpointProfile(2, 2, 2, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.72, 0.28, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 25;
   }
   else if (rvltName == "ANWBrazil")
   {
      anwVerboseEcho("A New World: activating ANW Brazil Pedro II personality.");
      anwSetBalancedPersonality();
      btRushBoom = -0.15;
      btOffenseDefense = 0.25;
      btBiasTrade = 0.35;
      btBiasNative = 0.15;
      anwSetMilitaryFocus(0.55, 0.35, 0.45);
      // LL-BUILD-STYLE-BEGIN
      anwUseDistributedEconomicNetworkStyle(2);
      gANWEconomicDistanceMultiplier = 1.35;
      // Spec override: military_distance_band [1.1, 1.3]; DistributedEcoNetwork
      // default is 1.0 which falls below the band floor.
      gANWMilitaryDistanceMultiplier = 1.10;
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.8, 0.2, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 26;
   }
   else if (rvltName == "ANWCanadians")
   {
      anwVerboseEcho("A New World: activating ANW Canadians Brock personality.");
      anwSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = -0.2;
      btBiasTrade = 0.25;
      btBiasNative = 0.1;
      anwSetMilitaryFocus(0.85, -0.2, 0.35);
      // LL-BUILD-STYLE-BEGIN
      anwUseCompactFortifiedCoreStyle(2, true);  // earlyWalls=true to meet spec first_wall_before_ms=600000.
      gANWEconomicDistanceMultiplier = 0.95;
      gANWMilitaryDistanceMultiplier = 0.85;  // Spec band [0.7,0.9]: frontier blockhouse defense.
      anwSetBuildStrongpointProfile(2, 2, 2, false);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.86, 0.14, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 9;
      cvMaxArmyPop = 110;
      gRvltCivId = 27;
   }
   else if (rvltName == "ANWChileans")
   {
      anwVerboseEcho("A New World: activating ANW Chileans O'Higgins personality.");
      // Balanced posture matches the defensive AndeanTerraceFortress doctrine
      // and harmonises with ANWChileans (audit v2 flagged the prior 0.5 /
      // Aggressive split as a design tension; later Age rules still escalate
      // offensive bias as the liberation campaign matures).
      anwSetBalancedPersonality();
      btRushBoom = -0.1;
      btOffenseDefense = 0.35;
      btBiasTrade = 0.2;
      btBiasNative = 0.1;
      anwSetMilitaryFocus(0.7, 0.55, 0.3);
      // LL-BUILD-STYLE-BEGIN
      anwUseAndeanTerraceFortressStyle(2);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 2, 2, false);
      // Spec override: Chileans O'Higgins doctrine — see playstyle_spec.json
      gANWWallStrategy = cANWWallStrategyFortressRing;
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.75, 0.25, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 28;
   }
   else if (rvltName == "ANWColumbians")
   {
      anwVerboseEcho("A New World: activating ANW Columbians Bolivar personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.15;
      btBiasNative = 0.2;
      anwSetMilitaryFocus(0.45, 0.7, 0.3);
      // LL-BUILD-STYLE-BEGIN
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(1, 1, 3, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.72, 0.28, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 120;
      gRvltCivId = 29;
   }
   else if (rvltName == "ANWEgyptians")
   {
      anwVerboseEcho("A New World: activating ANW Egyptians Muhammad Ali personality.");
      anwSetBalancedPersonality();
      btRushBoom = -0.15;
      btOffenseDefense = 0.4;
      btBiasTrade = 0.35;
      btBiasNative = 0.0;
      anwSetMilitaryFocus(0.7, 0.3, 0.55);
      // LL-BUILD-STYLE-BEGIN
      anwUseHighlandCitadelStyle(4);
      gANWHouseDistanceMultiplier = 0.75;
      gANWMilitaryDistanceMultiplier = 0.85;  // Nizam-i Cedid citadel — mid-band of spec [0.7,1.0]; mirrors ANWEgyptians.
      anwSetBuildStrongpointProfile(3, 3, 2, false);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 120;
      gRvltCivId = 30;
   }
   else if (rvltName == "ANWFinnish")
   {
      anwVerboseEcho("A New World: activating ANW Finnish Mannerheim personality.");
      anwSetDefensivePersonality();
      btRushBoom = -0.3;
      btOffenseDefense = -0.05;
      btBiasTrade = -0.05;
      btBiasNative = 0.15;
      anwSetMilitaryFocus(0.85, -0.1, 0.4);
      // LL-BUILD-STYLE-BEGIN
      anwUseCompactFortifiedCoreStyle(3, true);
      gANWHouseDistanceMultiplier = 0.80;
      gANWMilitaryDistanceMultiplier = 0.85;  // Spec band [0.7,0.9]: Mannerheim Line fortified depth.
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.86, 0.14, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 9;
      cvMaxArmyPop = 110;
      gRvltCivId = 31;
   }
   else if (rvltName == "ANWHaitians")
   {
      anwVerboseEcho("A New World: activating ANW Haitians Toussaint personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = 0.15;
      btBiasNative = 0.65;
      anwSetMilitaryFocus(0.85, 0.15, 0.15);
      // LL-BUILD-STYLE-BEGIN
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWEconomicDistanceMultiplier = 1.40;
      gANWTownCenterDistanceMultiplier = 1.40;
      // Spec override: Haitians Louverture doctrine — see playstyle_spec.json
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      // Spec override: military_distance_band [1.0, 1.3]; JungleGuerrilla
      // default is 0.95 which falls below the band floor.
      gANWMilitaryDistanceMultiplier = 1.10;
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 125;
      gRvltCivId = 32;
   }
   else if (rvltName == "ANWHungarians")
   {
      anwVerboseEcho("A New World: activating ANW Hungarians Kossuth personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.15;
      btBiasNative = 0.0;
      anwSetMilitaryFocus(0.55, 0.7, 0.25);
      // LL-BUILD-STYLE-BEGIN
      anwUseSteppeCavalryWedgeStyle(1);
      gANWMilitaryDistanceMultiplier = 1.15;  // Spec band [1.1,1.3]: Honved hussar forward charge.
      anwSetBuildStrongpointProfile(2, 1, 3, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.74, 0.26, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 115;
      gRvltCivId = 33;
   }
   else if (rvltName == "ANWIndonesians")
   {
      anwVerboseEcho("A New World: activating ANW Indonesians Diponegoro personality.");
      anwSetDefensivePersonality();
      btRushBoom = -0.2;
      btOffenseDefense = -0.05;
      btBiasTrade = 0.3;
      btBiasNative = 0.55;
      anwSetMilitaryFocus(0.8, -0.1, 0.2);
      // LL-BUILD-STYLE-BEGIN
      anwUseJungleGuerrillaNetworkStyle(0);
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      gANWEconomicDistanceMultiplier = 1.40;
      // Spec override: military_distance_band [1.0, 1.3]; JungleGuerrillaNetwork
      // default is 0.95 which falls below the band floor.
      gANWMilitaryDistanceMultiplier = 1.05;
      // Spec doctrine_summary: "Java War guerrilla and kraton fort" — keep
      // the single kraton fort (fort=1, matching JungleGuerrillaNetwork default).
      // Forward-fortified base preferred (preferFwd=true) for warband staging.
      anwSetBuildStrongpointProfile(1, 1, 2, true);
      anwSetPreferredTerrain(cANWTerrainJungle, cANWTerrainCoast, 0.40);
      anwSetExpansionHeading(cANWHeadingIslandHop, 0.35);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 115;
      gRvltCivId = 34;
   }
   else if (rvltName == "ANWMayans")
   {
      anwVerboseEcho("A New World: activating ANW Mayans Caste War personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = 0.1;
      btBiasNative = 0.85;
      anwSetMilitaryFocus(0.95, -0.2, 0.0);
      // LL-BUILD-STYLE-BEGIN
      anwUseJungleGuerrillaNetworkStyle(1);
      gANWMilitaryDistanceMultiplier = 1.0;   // Spec band [1.0,1.3]: insurgent network spreads forward.
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      // Spec override: Mayans Canek doctrine — see playstyle_spec.json
      gANWWallStrategy = cANWWallStrategyChokepointSegments;
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 125;
      gRvltCivId = 35;
   }
   else if (rvltName == "ANWMexicans")
   {
      anwVerboseEcho("A New World: activating ANW Mexicans Hidalgo personality.");
      anwSetBalancedPersonality();
      btRushBoom = -0.1;
      btOffenseDefense = 0.4;
      btBiasTrade = 0.1;
      btBiasNative = 0.2;
      anwSetMilitaryFocus(0.75, 0.25, 0.3);
      // LL-BUILD-STYLE-BEGIN
      anwUseRepublicanLeveeStyle(1);
      // Spec claim wall_strategy=4 (UrbanBarricade); anwUseRepublicanLeveeStyle
      // sets gANWWallStrategy = cANWWallStrategyUrbanBarricade directly.
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.76, 0.24, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 36;
   }
   else if (rvltName == "ANWNapoleonicFrance")
   {
      anwVerboseEcho("A New World: activating ANW NapoleonicFrance Napoleon personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.1;
      btOffenseDefense = 0.75;
      btBiasTrade = 0.0;
      btBiasNative = -0.1;
      anwSetMilitaryFocus(0.75, 0.55, 0.55);
      // LL-BUILD-STYLE-BEGIN
      anwUseForwardOperationalLineStyle(0);
      // Spec claim wall_strategy=5 (MobileNoWalls); anwUseForwardOperationalLine
      // sets gANWWallStrategy = cANWWallStrategyMobileNoWalls directly.
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 135;
      gRvltCivId = 37;
   }
   else if (rvltName == "ANWPeruvians")
   {
      anwVerboseEcho("A New World: activating ANW Peruvians Santa Cruz personality.");
      anwSetDefensivePersonality();
      btRushBoom = -0.3;
      btOffenseDefense = -0.1;
      btBiasTrade = 0.2;
      btBiasNative = 0.55;
      anwSetMilitaryFocus(0.7, 0.05, 0.3);
      // LL-BUILD-STYLE-BEGIN
      anwUseAndeanTerraceFortressStyle(3);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(3, 2, 2, false);
      // Spec override: Peruvians Santa Cruz doctrine — see playstyle_spec.json
      gANWWallStrategy = cANWWallStrategyFortressRing;
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 115;
      gRvltCivId = 38;
   }
   else if (rvltName == "ANWRevFrance")
   {
      anwVerboseEcho("A New World: activating ANW RevFrance Robespierre personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.25;
      btBiasNative = -0.2;
      anwSetMilitaryFocus(0.95, 0.0, 0.3);
      // LL-BUILD-STYLE-BEGIN
      anwUseRepublicanLeveeStyle(1);  // wallLevel=1 (minimum palisade ring) to satisfy spec first_wall_before_ms=900000; "tight inner defense only" doctrine still preserved.
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(1, 1, 3, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 130;
      gRvltCivId = 39;
   }
   else if (rvltName == "ANWRomanians")
   {
      anwVerboseEcho("A New World: activating ANW Romanians Cuza personality.");
      anwSetDefensivePersonality();
      btRushBoom = -0.25;
      btOffenseDefense = 0.05;
      btBiasTrade = 0.3;
      btBiasNative = 0.05;
      anwSetMilitaryFocus(0.65, 0.3, 0.4);
      // LL-BUILD-STYLE-BEGIN
      anwUseCivicMilitiaCenterStyle(2);
      gANWEconomicDistanceMultiplier = 1.10;
      anwSetBuildStrongpointProfile(2, 1, 2, false);
      // Spec claim: expects_forward not set (reactive consolidation, 1859
      // unification was internal). Reset forward base to engine default.
      gANWForwardBaseEarliestMs = 1200000;
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 110;
      gRvltCivId = 40;
   }
   else if (rvltName == "ANWSouthAfricans")
   {
      anwVerboseEcho("A New World: activating ANW SouthAfricans Kruger personality.");
      anwSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = 0.0;
      btBiasTrade = 0.5;
      btBiasNative = -0.1;
      anwSetMilitaryFocus(0.4, 0.6, 0.25);
      // LL-BUILD-STYLE-BEGIN
      anwUseNavalMercantileCompoundStyle(2);  // wallLevel=2 for a full Boer laager / harbor ring (was 1, lighter than spec expects).
      gANWEconomicDistanceMultiplier = 1.25;
      anwSetBuildStrongpointProfile(2, 1, 2, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 110;
      gRvltCivId = 41;
   }
   else if (rvltName == "ANWTexians")
   {
      anwVerboseEcho("A New World: activating ANW Texians Sam Houston personality.");
      anwSetAggressivePersonality();
      btRushBoom = 0.0;
      btOffenseDefense = 0.55;
      btBiasTrade = 0.1;
      btBiasNative = 0.1;
      anwSetMilitaryFocus(0.6, 0.65, 0.25);
      // LL-BUILD-STYLE-BEGIN
      anwUseForwardOperationalLineStyle(0);
      gANWMilitaryDistanceMultiplier = 0.90;
      anwSetBuildStrongpointProfile(2, 1, 3, true);
      // LL-BUILD-STYLE-END
      anwSetLeaderTacticalDoctrine(0.75, 0.25, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 42;
   }
   else
   {
      return;
   }

   debugANW("revolution commander initialized for " + rvltName + " (civId " + gRvltCivId + ")");
   gANWRevolutionCommanderEnabled = true;
   anwLogLeaderState("revolution commander initialized for " + rvltName);
   // Replay probe: confirms which revolution commander block ran. The civ
   // name is the only stable key here (gANWLeaderKey is set later by
   // anwAssignLeaderIdentity). gRvltCivId is the per-block ordinal.
   anwProbe("meta.leader_init", "leader=rvlt_" + rvltName + " rvltCivId=" + gRvltCivId);
}

//------------------------------------------------------------------------------
// Discovery: per-civ economic / opening tilt.
//------------------------------------------------------------------------------
rule rvltAge1Discovery
inactive
minInterval 60
{
   anwLogRuleTick("rvltAge1Discovery");
   if (gANWRevolutionCommanderEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() > cAge1)
   {
      return;
   }

   if (gRvltCivId == 1)        { btRushBoom = -0.5; btBiasTrade = 0.4;  cvMinNumVills = 18; }
   else if (gRvltCivId == 2)   { btRushBoom = -0.1; btBiasNative = -0.3; cvMinNumVills = 16; }
   else if (gRvltCivId == 3)   { btRushBoom = -0.45; btBiasTrade = 0.5;  cvMinNumVills = 18; }
   else if (gRvltCivId == 4)   { btRushBoom = -0.3; btBiasTrade = 0.5;  cvMinNumVills = 17; }
   else if (gRvltCivId == 5)   { btRushBoom = -0.15; btBiasNative = 0.2; cvMinNumVills = 15; }
   else if (gRvltCivId == 6)   { btRushBoom = -0.25; btBiasTrade = 0.4;  cvMinNumVills = 17; }
   else if (gRvltCivId == 7)   { btRushBoom = -0.45; btBiasNative = 0.7; cvMinNumVills = 18; }
   else if (gRvltCivId == 8)   { btRushBoom = -0.15; btBiasTrade = 0.3;  cvMinNumVills = 15; }
   else if (gRvltCivId == 9)   { btRushBoom = -0.1; btBiasNative = 0.75; cvMinNumVills = 16; }
   else if (gRvltCivId == 10)  { btRushBoom = -0.35; btBiasNative = 0.7; cvMinNumVills = 17; }
   else if (gRvltCivId == 11)  { btRushBoom = -0.5; btBiasTrade = 0.65; cvMinNumVills = 18; }
   else if (gRvltCivId == 12)  { btRushBoom = -0.45; btBiasNative = 0.25; cvMinNumVills = 18; }
   else if (gRvltCivId == 13)  { btRushBoom = -0.1; btBiasTrade = 0.3;  cvMinNumVills = 15; }
   else if (gRvltCivId == 14)  { btRushBoom = -0.4; btBiasTrade = 0.45; cvMinNumVills = 18; }
   else if (gRvltCivId == 15)  { btRushBoom = -0.15; btBiasTrade = 0.65; cvMinNumVills = 16; }
   else if (gRvltCivId == 16)  { btRushBoom = -0.3; btBiasTrade = 0.5;  cvMinNumVills = 18; }
   else if (gRvltCivId == 17)  { btRushBoom = -0.25; btBiasNative = 0.65; cvMinNumVills = 17; }
   else if (gRvltCivId == 18)  { btRushBoom = -0.1; btBiasTrade = 0.35; cvMinNumVills = 15; }
   else if (gRvltCivId == 19)  { btRushBoom = -0.2; btBiasNative = 0.8;  cvMinNumVills = 17; }
   else if (gRvltCivId == 20)  { btRushBoom = -0.1; btBiasTrade = 0.0;   cvMinNumVills = 15; }
   else if (gRvltCivId == 21)  { btRushBoom = -0.1; btBiasNative = 0.9;  cvMinNumVills = 16; }
   else if (gRvltCivId == 22)  { btRushBoom = -0.5; btBiasTrade = 0.7;   cvMinNumVills = 18; }
   else if (gRvltCivId == 23)  { btRushBoom = -0.4; btBiasTrade = 0.3;   cvMinNumVills = 18; }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btRushBoom = -0.15; btBiasNative = 0.2;  cvMinNumVills = 15; } // ANWArgentines
   else if (gRvltCivId == 25)  { btRushBoom = -0.15; btBiasTrade = 0.65;  cvMinNumVills = 16; } // ANWBarbary
   else if (gRvltCivId == 26)  { btRushBoom = -0.3;  btBiasTrade = 0.5;   cvMinNumVills = 17; } // ANWBrazil
   else if (gRvltCivId == 27)  { btRushBoom = -0.5;  btBiasTrade = 0.4;   cvMinNumVills = 18; } // ANWCanadians
   else if (gRvltCivId == 28)  { btRushBoom = -0.2;  btBiasTrade = 0.3;   cvMinNumVills = 16; } // ANWChileans
   else if (gRvltCivId == 29)  { btRushBoom = -0.15; btBiasNative = 0.25; cvMinNumVills = 15; } // ANWColumbians
   else if (gRvltCivId == 30)  { btRushBoom = -0.3;  btBiasTrade = 0.5;   cvMinNumVills = 18; } // ANWEgyptians
   else if (gRvltCivId == 31)  { btRushBoom = -0.45; btBiasNative = 0.25; cvMinNumVills = 18; } // ANWFinnish
   else if (gRvltCivId == 32)  { btRushBoom = -0.1;  btBiasNative = 0.75; cvMinNumVills = 16; } // ANWHaitians
   else if (gRvltCivId == 33)  { btRushBoom = -0.1;  btBiasTrade = 0.3;   cvMinNumVills = 15; } // ANWHungarians
   else if (gRvltCivId == 34)  { btRushBoom = -0.35; btBiasNative = 0.7;  cvMinNumVills = 17; } // ANWIndonesians
   else if (gRvltCivId == 35)  { btRushBoom = -0.1;  btBiasNative = 0.9;  cvMinNumVills = 16; } // ANWMayans
   else if (gRvltCivId == 36)  { btRushBoom = -0.2;  btBiasNative = 0.25; cvMinNumVills = 17; } // ANWMexicans
   else if (gRvltCivId == 37)  { btRushBoom = -0.05; btBiasTrade = 0.1;   cvMinNumVills = 15; } // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btRushBoom = -0.45; btBiasNative = 0.7;  cvMinNumVills = 18; } // ANWPeruvians
   else if (gRvltCivId == 39)  { btRushBoom = -0.1;  btBiasNative = -0.3; cvMinNumVills = 16; } // ANWRevFrance
   else if (gRvltCivId == 40)  { btRushBoom = -0.4;  btBiasTrade = 0.45;  cvMinNumVills = 18; } // ANWRomanians
   else if (gRvltCivId == 41)  { btRushBoom = -0.5;  btBiasTrade = 0.65;  cvMinNumVills = 18; } // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btRushBoom = -0.15; btBiasNative = 0.15; cvMinNumVills = 16; } // ANWTexians
}

//------------------------------------------------------------------------------
// Colonial: per-civ opening composition and posture.
//------------------------------------------------------------------------------
rule rvltAge2Colonial
inactive
minInterval 50
{
   anwLogRuleTick("rvltAge2Colonial");
   if (gANWRevolutionCommanderEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() != cAge2)
   {
      return;
   }

   // Brock: defensive infantry behind blockhouses.
   if (gRvltCivId == 1)        { btOffenseDefense = -0.05; btBiasInf = 0.85; btBiasCav = -0.2; btBiasArt = -0.1; cvMinNumVills = 32; }
   // Robespierre: levee surge.
   else if (gRvltCivId == 2)   { btOffenseDefense = 0.75; btBiasInf = 0.95; btBiasCav = 0.2; btBiasArt = -0.1; anwEnableForwardBaseStyle(); }
   // Pedro I: Imperial line + Hessian mercenary trickle.
   else if (gRvltCivId == 4)   { btOffenseDefense = 0.4; btBiasInf = 0.7; btBiasCav = 0.45; btBiasArt = 0.2; }
   // San Martin: Granadero a Caballo.
   else if (gRvltCivId == 5)   { btOffenseDefense = 0.7; btBiasInf = 0.4; btBiasCav = 0.85; btBiasArt = -0.2; anwEnableForwardBaseStyle(); }
   // O'Higgins: balanced Republican infantry.
   else if (gRvltCivId == 6)   { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.4; btBiasArt = 0.0; }
   // Santa Cruz: Andean fort line, native muster.
   else if (gRvltCivId == 7)   { btOffenseDefense = -0.05; btBiasInf = 0.9; btBiasCav = 0.05; btBiasArt = -0.1; cvMinNumVills = 30; }
   // Bolivar: Llanero horse sweeps.
   else if (gRvltCivId == 8)   { btOffenseDefense = 0.7; btBiasInf = 0.5; btBiasCav = 0.85; btBiasArt = -0.1; anwEnableForwardBaseStyle(); }
   // Toussaint: mass infantry insurrection.
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.1; btBiasArt = -0.3; anwEnableForwardBaseStyle(); }
   // Diponegoro: Java War guerrilla and fortified kraton.
   else if (gRvltCivId == 10)  { btOffenseDefense = 0.0; btBiasInf = 0.9; btBiasCav = -0.1; btBiasArt = -0.2; cvMinNumVills = 30; }
   // Kruger: Boer commando trader-cavalry.
   else if (gRvltCivId == 11)  { btOffenseDefense = 0.05; btBiasInf = 0.4; btBiasCav = 0.7; btBiasArt = -0.1; cvMinNumVills = 30; }
   // Mannerheim: ski infantry behind frontier line.
   else if (gRvltCivId == 12)  { btOffenseDefense = -0.05; btBiasInf = 0.95; btBiasCav = -0.1; btBiasArt = 0.0; cvMinNumVills = 32; }
   // Kossuth: Honved hussar uprising.
   else if (gRvltCivId == 13)  { btOffenseDefense = 0.7; btBiasInf = 0.65; btBiasCav = 0.85; btBiasArt = -0.1; anwEnableForwardBaseStyle(); }
   // Cuza: Danubian principalities consolidation.
   else if (gRvltCivId == 14)  { btOffenseDefense = 0.15; btBiasInf = 0.8; btBiasCav = 0.4; btBiasArt = 0.05; }
   // Barbarossa: corsair raid.
   else if (gRvltCivId == 15)  { btOffenseDefense = 0.7; btBiasInf = 0.45; btBiasCav = 0.75; btBiasArt = -0.2; anwEnableForwardBaseStyle(); }
   // Muhammad Ali: Nizam-i Cedid line.
   else if (gRvltCivId == 16)  { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.35; btBiasArt = 0.1; }
   // Morazan: Federal Republic native muster.
   else if (gRvltCivId == 17)  { btOffenseDefense = 0.4; btBiasInf = 0.85; btBiasCav = 0.3; btBiasArt = -0.1; }
   // Alvarado: Californio horse raid.
   else if (gRvltCivId == 18)  { btOffenseDefense = 0.65; btBiasInf = 0.3; btBiasCav = 0.85; btBiasArt = -0.3; anwEnableForwardBaseStyle(); }
   // Carrillo Puerto: Maya levy mass.
   else if (gRvltCivId == 19)  { btOffenseDefense = 0.55; btBiasInf = 0.95; btBiasCav = 0.05; btBiasArt = -0.3; }
   // Canales: Rio Grande horse.
   else if (gRvltCivId == 20)  { btOffenseDefense = 0.75; btBiasInf = 0.4; btBiasCav = 0.85; btBiasArt = -0.2; anwEnableForwardBaseStyle(); }
   // Canek: indigenous insurrection mass.
   else if (gRvltCivId == 21)  { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = -0.2; btBiasArt = -0.4; anwEnableForwardBaseStyle(); }
   // Vallejo: ranchero defense and trade.
   else if (gRvltCivId == 22)  { btOffenseDefense = -0.1; btBiasInf = 0.45; btBiasCav = 0.6; btBiasArt = -0.1; cvMinNumVills = 30; }
   // Houston: Republic of Texas militia.
   else if (gRvltCivId == 23)  { btOffenseDefense = 0.05; btBiasInf = 0.75; btBiasCav = 0.55; btBiasArt = -0.1; cvMinNumVills = 30; }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btOffenseDefense = 0.7;  btBiasInf = 0.4;  btBiasCav = 0.85; btBiasArt = -0.2; anwEnableForwardBaseStyle(); }  // ANWArgentines
   else if (gRvltCivId == 25)  { btOffenseDefense = 0.65; btBiasInf = 0.45; btBiasCav = 0.75; btBiasArt = -0.2; anwEnableForwardBaseStyle(); }  // ANWBarbary
   else if (gRvltCivId == 26)  { btOffenseDefense = 0.4;  btBiasInf = 0.7;  btBiasCav = 0.45; btBiasArt = 0.2;  }                              // ANWBrazil
   else if (gRvltCivId == 27)  { btOffenseDefense = -0.05; btBiasInf = 0.85; btBiasCav = -0.2; btBiasArt = -0.1; cvMinNumVills = 32; }          // ANWCanadians
   else if (gRvltCivId == 28)  { btOffenseDefense = 0.55; btBiasInf = 0.75; btBiasCav = 0.65; btBiasArt = 0.05; }                              // ANWChileans
   else if (gRvltCivId == 29)  { btOffenseDefense = 0.7;  btBiasInf = 0.5;  btBiasCav = 0.85; btBiasArt = -0.1; anwEnableForwardBaseStyle(); }  // ANWColumbians
   else if (gRvltCivId == 30)  { btOffenseDefense = 0.45; btBiasInf = 0.75; btBiasCav = 0.35; btBiasArt = 0.35; }                              // ANWEgyptians (Muhammad Ali: Nizam-i Cedid artillery modernization — Age2 ramps art from 0.1→0.35 to honour expects_artillery=true spec claim; Age3 commits to 0.7)
   else if (gRvltCivId == 31)  { btOffenseDefense = -0.05; btBiasInf = 0.95; btBiasCav = -0.1; btBiasArt = 0.0;  cvMinNumVills = 32; }          // ANWFinnish
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.75; btBiasInf = 1.0;  btBiasCav = 0.1;  btBiasArt = -0.3; anwEnableForwardBaseStyle(); }  // ANWHaitians
   else if (gRvltCivId == 33)  { btOffenseDefense = 0.7;  btBiasInf = 0.65; btBiasCav = 0.85; btBiasArt = -0.1; anwEnableForwardBaseStyle(); }  // ANWHungarians
   else if (gRvltCivId == 34)  { btOffenseDefense = 0.25; btBiasInf = 0.9;  btBiasCav = -0.1; btBiasArt = -0.2; anwEnableForwardBaseStyle(); } // ANWIndonesians (spec expects_forward=true)
   else if (gRvltCivId == 35)  { btOffenseDefense = 0.8;  btBiasInf = 1.0;  btBiasCav = -0.2; btBiasArt = -0.4; anwEnableForwardBaseStyle(); }  // ANWMayans
   else if (gRvltCivId == 36)  { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.3;  btBiasArt = -0.1; }                              // ANWMexicans
   else if (gRvltCivId == 37)  { btOffenseDefense = 0.75; btBiasInf = 0.9;  btBiasCav = 0.6;  btBiasArt = 0.2;  anwEnableForwardBaseStyle(); }  // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btOffenseDefense = -0.05; btBiasInf = 0.9;  btBiasCav = 0.05; btBiasArt = -0.1; cvMinNumVills = 30; }          // ANWPeruvians
   else if (gRvltCivId == 39)  { btOffenseDefense = 0.75; btBiasInf = 0.95; btBiasCav = 0.2;  btBiasArt = -0.1; anwEnableForwardBaseStyle(); }  // ANWRevFrance
   else if (gRvltCivId == 40)  { btOffenseDefense = 0.15; btBiasInf = 0.8;  btBiasCav = 0.4;  btBiasArt = 0.05; }                              // ANWRomanians
   else if (gRvltCivId == 41)  { btOffenseDefense = 0.05; btBiasInf = 0.4;  btBiasCav = 0.7;  btBiasArt = -0.1; cvMinNumVills = 30; }          // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btOffenseDefense = 0.6;  btBiasInf = 0.65; btBiasCav = 0.8;  btBiasArt = -0.1; anwEnableForwardBaseStyle(); }  // ANWTexians
}

//------------------------------------------------------------------------------
// Fortress: signature doctrine assembles.
//------------------------------------------------------------------------------
rule rvltAge3Fortress
inactive
minInterval 55
{
   anwLogRuleTick("rvltAge3Fortress");
   if (gANWRevolutionCommanderEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() != cAge3)
   {
      return;
   }

   if (gRvltCivId == 1)        { btOffenseDefense = 0.3; btBiasInf = 1.0; btBiasCav = -0.1; btBiasArt = 0.45; cvMaxArmyPop = 125; cvMaxTowers = 10; }
   else if (gRvltCivId == 2)   { btOffenseDefense = 0.85; btBiasInf = 1.0; btBiasCav = 0.4; btBiasArt = 0.5; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 3)   { btOffenseDefense = 0.3; btBiasInf = 1.0; btBiasCav = 0.25; btBiasArt = 0.25; cvMaxArmyPop = 125; cvMaxTowers = 8; }
   else if (gRvltCivId == 4)   { btOffenseDefense = 0.55; btBiasInf = 0.9; btBiasCav = 0.55; btBiasArt = 0.6; cvMaxArmyPop = 130; }
   else if (gRvltCivId == 5)   { btOffenseDefense = 0.8; btBiasInf = 0.55; btBiasCav = 0.95; btBiasArt = 0.25; cvMaxArmyPop = 130; }
   else if (gRvltCivId == 6)   { btOffenseDefense = 0.6; btBiasInf = 0.95; btBiasCav = 0.55; btBiasArt = 0.45; cvMaxArmyPop = 130; }
   else if (gRvltCivId == 7)   { btOffenseDefense = 0.35; btBiasInf = 1.0; btBiasCav = 0.2; btBiasArt = 0.45; cvMaxArmyPop = 130; cvMaxTowers = 9; }
   else if (gRvltCivId == 8)   { btOffenseDefense = 0.8; btBiasInf = 0.7; btBiasCav = 0.95; btBiasArt = 0.4; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.85; btBiasInf = 1.0; btBiasCav = 0.3; btBiasArt = 0.2; cvMaxArmyPop = 140; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 10)  { btOffenseDefense = 0.4; btBiasInf = 1.0; btBiasCav = 0.05; btBiasArt = 0.35; cvMaxArmyPop = 130; cvMaxTowers = 9; }
   else if (gRvltCivId == 11)  { btOffenseDefense = 0.45; btBiasInf = 0.55; btBiasCav = 0.85; btBiasArt = 0.4; cvMaxArmyPop = 125; cvMaxTowers = 9; }
   else if (gRvltCivId == 12)  { btOffenseDefense = 0.2; btBiasInf = 1.0; btBiasCav = -0.05; btBiasArt = 0.55; cvMaxArmyPop = 125; cvMaxTowers = 11; }
   else if (gRvltCivId == 13)  { btOffenseDefense = 0.8; btBiasInf = 0.75; btBiasCav = 0.95; btBiasArt = 0.4; cvMaxArmyPop = 130; }
   else if (gRvltCivId == 14)  { btOffenseDefense = 0.45; btBiasInf = 0.9; btBiasCav = 0.5; btBiasArt = 0.55; cvMaxArmyPop = 125; cvMaxTowers = 8; }
   else if (gRvltCivId == 15)  { btOffenseDefense = 0.8; btBiasInf = 0.55; btBiasCav = 0.85; btBiasArt = 0.3; cvMaxArmyPop = 125; }
   else if (gRvltCivId == 16)  { btOffenseDefense = 0.7; btBiasInf = 0.95; btBiasCav = 0.5; btBiasArt = 0.7; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 17)  { btOffenseDefense = 0.65; btBiasInf = 0.95; btBiasCav = 0.4; btBiasArt = 0.3; cvMaxArmyPop = 130; }
   else if (gRvltCivId == 18)  { btOffenseDefense = 0.75; btBiasInf = 0.4; btBiasCav = 0.95; btBiasArt = 0.0; cvMaxArmyPop = 125; }
   else if (gRvltCivId == 19)  { btOffenseDefense = 0.7; btBiasInf = 1.0; btBiasCav = 0.15; btBiasArt = 0.0; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 20)  { btOffenseDefense = 0.85; btBiasInf = 0.5; btBiasCav = 0.95; btBiasArt = 0.15; cvMaxArmyPop = 125; }
   else if (gRvltCivId == 21)  { btOffenseDefense = 0.9; btBiasInf = 1.0; btBiasCav = -0.1; btBiasArt = -0.2; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 22)  { btOffenseDefense = 0.2; btBiasInf = 0.55; btBiasCav = 0.7; btBiasArt = 0.4; cvMaxArmyPop = 125; cvMaxTowers = 8; }
   else if (gRvltCivId == 23)  { btOffenseDefense = 0.45; btBiasInf = 0.9; btBiasCav = 0.65; btBiasArt = 0.3; cvMaxArmyPop = 130; cvMaxTowers = 8; }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btOffenseDefense = 0.8;  btBiasInf = 0.55; btBiasCav = 0.95; btBiasArt = 0.25; cvMaxArmyPop = 130; }            // ANWArgentines
   else if (gRvltCivId == 25)  { btOffenseDefense = 0.75; btBiasInf = 0.55; btBiasCav = 0.85; btBiasArt = 0.3;  cvMaxArmyPop = 125; }            // ANWBarbary
   else if (gRvltCivId == 26)  { btOffenseDefense = 0.55; btBiasInf = 0.9;  btBiasCav = 0.55; btBiasArt = 0.6;  cvMaxArmyPop = 130; }            // ANWBrazil
   else if (gRvltCivId == 27)  { btOffenseDefense = 0.3;  btBiasInf = 1.0;  btBiasCav = -0.1; btBiasArt = 0.45; cvMaxArmyPop = 125; cvMaxTowers = 10; } // ANWCanadians
   else if (gRvltCivId == 28)  { btOffenseDefense = 0.65; btBiasInf = 0.95; btBiasCav = 0.65; btBiasArt = 0.45; cvMaxArmyPop = 130; }            // ANWChileans
   else if (gRvltCivId == 29)  { btOffenseDefense = 0.8;  btBiasInf = 0.7;  btBiasCav = 0.95; btBiasArt = 0.4;  cvMaxArmyPop = 135; }            // ANWColumbians
   else if (gRvltCivId == 30)  { btOffenseDefense = 0.7;  btBiasInf = 0.95; btBiasCav = 0.5;  btBiasArt = 0.7;  cvMaxArmyPop = 135; }            // ANWEgyptians
   else if (gRvltCivId == 31)  { btOffenseDefense = 0.2;  btBiasInf = 1.0;  btBiasCav = -0.05; btBiasArt = 0.55; cvMaxArmyPop = 125; cvMaxTowers = 11; } // ANWFinnish
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.85; btBiasInf = 1.0;  btBiasCav = 0.3;  btBiasArt = 0.2;  cvMaxArmyPop = 140; anwEnableForwardBaseStyle(); } // ANWHaitians
   else if (gRvltCivId == 33)  { btOffenseDefense = 0.8;  btBiasInf = 0.75; btBiasCav = 0.95; btBiasArt = 0.4;  cvMaxArmyPop = 130; }            // ANWHungarians
   else if (gRvltCivId == 34)  { btOffenseDefense = 0.4;  btBiasInf = 1.0;  btBiasCav = 0.05; btBiasArt = 0.35; cvMaxArmyPop = 130; cvMaxTowers = 9; } // ANWIndonesians
   else if (gRvltCivId == 35)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = -0.1; btBiasArt = -0.2; cvMaxArmyPop = 140; }            // ANWMayans
   else if (gRvltCivId == 36)  { btOffenseDefense = 0.6;  btBiasInf = 0.95; btBiasCav = 0.45; btBiasArt = 0.3;  cvMaxArmyPop = 130; }            // ANWMexicans
   else if (gRvltCivId == 37)  { btOffenseDefense = 0.85; btBiasInf = 0.9;  btBiasCav = 0.75; btBiasArt = 0.6;  cvMaxArmyPop = 145; }            // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btOffenseDefense = 0.35; btBiasInf = 1.0;  btBiasCav = 0.2;  btBiasArt = 0.45; cvMaxArmyPop = 130; cvMaxTowers = 9; } // ANWPeruvians
   else if (gRvltCivId == 39)  { btOffenseDefense = 0.85; btBiasInf = 1.0;  btBiasCav = 0.4;  btBiasArt = 0.5;  cvMaxArmyPop = 145; }            // ANWRevFrance
   else if (gRvltCivId == 40)  { btOffenseDefense = 0.45; btBiasInf = 0.9;  btBiasCav = 0.5;  btBiasArt = 0.55; cvMaxArmyPop = 125; cvMaxTowers = 8; } // ANWRomanians
   else if (gRvltCivId == 41)  { btOffenseDefense = 0.45; btBiasInf = 0.55; btBiasCav = 0.85; btBiasArt = 0.4;  cvMaxArmyPop = 125; cvMaxTowers = 9; } // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btOffenseDefense = 0.7;  btBiasInf = 0.8;  btBiasCav = 0.85; btBiasArt = 0.25; cvMaxArmyPop = 130; }            // ANWTexians
}

//------------------------------------------------------------------------------
// Industrial: deep operational tempo.
//------------------------------------------------------------------------------
rule rvltAge4Industrial
inactive
minInterval 70
{
   anwLogRuleTick("rvltAge4Industrial");
   if (gANWRevolutionCommanderEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() != cAge4)
   {
      return;
   }

   if (gRvltCivId == 1)        { btOffenseDefense = 0.5; btBiasInf = 1.0; btBiasCav = 0.1; btBiasArt = 0.65; cvMaxArmyPop = 140; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 2)   { btOffenseDefense = 0.9; btBiasInf = 1.0; btBiasCav = 0.5; btBiasArt = 0.7; cvMaxArmyPop = 165; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 3)   { btOffenseDefense = 0.45; btBiasInf = 1.0; btBiasCav = 0.4; btBiasArt = 0.45; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 4)   { btOffenseDefense = 0.7; btBiasInf = 1.0; btBiasCav = 0.65; btBiasArt = 0.75; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 5)   { btOffenseDefense = 0.85; btBiasInf = 0.7; btBiasCav = 1.0; btBiasArt = 0.45; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 6)   { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.65; btBiasArt = 0.6; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 7)   { btOffenseDefense = 0.55; btBiasInf = 1.0; btBiasCav = 0.3; btBiasArt = 0.6; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 8)   { btOffenseDefense = 0.85; btBiasInf = 0.8; btBiasCav = 1.0; btBiasArt = 0.55; cvMaxArmyPop = 150; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.9; btBiasInf = 1.0; btBiasCav = 0.4; btBiasArt = 0.4; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 10)  { btOffenseDefense = 0.55; btBiasInf = 1.0; btBiasCav = 0.15; btBiasArt = 0.5; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 11)  { btOffenseDefense = 0.6; btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.55; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 12)  { btOffenseDefense = 0.4; btBiasInf = 1.0; btBiasCav = 0.05; btBiasArt = 0.7; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 13)  { btOffenseDefense = 0.85; btBiasInf = 0.85; btBiasCav = 1.0; btBiasArt = 0.55; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 14)  { btOffenseDefense = 0.6; btBiasInf = 1.0; btBiasCav = 0.55; btBiasArt = 0.7; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 15)  { btOffenseDefense = 0.85; btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.45; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 16)  { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = 0.55; btBiasArt = 0.85; cvMaxArmyPop = 150; anwEnableForwardBaseStyle(); }
   else if (gRvltCivId == 17)  { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.45; btBiasArt = 0.45; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 18)  { btOffenseDefense = 0.85; btBiasInf = 0.5; btBiasCav = 1.0; btBiasArt = 0.15; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 19)  { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = 0.25; btBiasArt = 0.2; cvMaxArmyPop = 150; }
   else if (gRvltCivId == 20)  { btOffenseDefense = 0.9; btBiasInf = 0.6; btBiasCav = 1.0; btBiasArt = 0.3; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 21)  { btOffenseDefense = 0.95; btBiasInf = 1.0; btBiasCav = 0.0; btBiasArt = -0.1; cvMaxArmyPop = 150; }
   else if (gRvltCivId == 22)  { btOffenseDefense = 0.4; btBiasInf = 0.65; btBiasCav = 0.8; btBiasArt = 0.55; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 23)  { btOffenseDefense = 0.6; btBiasInf = 1.0; btBiasCav = 0.7; btBiasArt = 0.5; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btOffenseDefense = 0.85; btBiasInf = 0.7;  btBiasCav = 1.0;  btBiasArt = 0.45; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); } // ANWArgentines
   else if (gRvltCivId == 25)  { btOffenseDefense = 0.85; btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.45; cvMaxArmyPop = 140; }                             // ANWBarbary
   else if (gRvltCivId == 26)  { btOffenseDefense = 0.7;  btBiasInf = 1.0;  btBiasCav = 0.65; btBiasArt = 0.75; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); } // ANWBrazil
   else if (gRvltCivId == 27)  { btOffenseDefense = 0.5;  btBiasInf = 1.0;  btBiasCav = 0.1;  btBiasArt = 0.65; cvMaxArmyPop = 140; anwEnableForwardBaseStyle(); } // ANWCanadians
   else if (gRvltCivId == 28)  { btOffenseDefense = 0.75; btBiasInf = 1.0;  btBiasCav = 0.75; btBiasArt = 0.6;  cvMaxArmyPop = 145; }                             // ANWChileans
   else if (gRvltCivId == 29)  { btOffenseDefense = 0.85; btBiasInf = 0.8;  btBiasCav = 1.0;  btBiasArt = 0.55; cvMaxArmyPop = 150; anwEnableForwardBaseStyle(); } // ANWColumbians
   else if (gRvltCivId == 30)  { btOffenseDefense = 0.8;  btBiasInf = 1.0;  btBiasCav = 0.55; btBiasArt = 0.85; cvMaxArmyPop = 150; anwEnableForwardBaseStyle(); } // ANWEgyptians
   else if (gRvltCivId == 31)  { btOffenseDefense = 0.4;  btBiasInf = 1.0;  btBiasCav = 0.05; btBiasArt = 0.7;  cvMaxArmyPop = 140; }                             // ANWFinnish
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.4;  btBiasArt = 0.4;  cvMaxArmyPop = 155; }                             // ANWHaitians
   else if (gRvltCivId == 33)  { btOffenseDefense = 0.85; btBiasInf = 0.85; btBiasCav = 1.0;  btBiasArt = 0.55; cvMaxArmyPop = 145; }                             // ANWHungarians
   else if (gRvltCivId == 34)  { btOffenseDefense = 0.55; btBiasInf = 1.0;  btBiasCav = 0.15; btBiasArt = 0.5;  cvMaxArmyPop = 140; }                             // ANWIndonesians
   else if (gRvltCivId == 35)  { btOffenseDefense = 0.95; btBiasInf = 1.0;  btBiasCav = 0.0;  btBiasArt = -0.1; cvMaxArmyPop = 150; }                             // ANWMayans
   else if (gRvltCivId == 36)  { btOffenseDefense = 0.7;  btBiasInf = 1.0;  btBiasCav = 0.5;  btBiasArt = 0.45; cvMaxArmyPop = 145; }                             // ANWMexicans
   else if (gRvltCivId == 37)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.8;  btBiasArt = 0.8;  cvMaxArmyPop = 160; anwEnableForwardBaseStyle(); } // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btOffenseDefense = 0.55; btBiasInf = 1.0;  btBiasCav = 0.3;  btBiasArt = 0.6;  cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); } // ANWPeruvians
   else if (gRvltCivId == 39)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.5;  btBiasArt = 0.7;  cvMaxArmyPop = 165; anwEnableForwardBaseStyle(); } // ANWRevFrance
   else if (gRvltCivId == 40)  { btOffenseDefense = 0.6;  btBiasInf = 1.0;  btBiasCav = 0.55; btBiasArt = 0.7;  cvMaxArmyPop = 140; }                             // ANWRomanians
   else if (gRvltCivId == 41)  { btOffenseDefense = 0.6;  btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.55; cvMaxArmyPop = 140; }                             // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btOffenseDefense = 0.75; btBiasInf = 0.9;  btBiasCav = 0.9;  btBiasArt = 0.45; cvMaxArmyPop = 145; anwEnableForwardBaseStyle(); } // ANWTexians
}

//------------------------------------------------------------------------------
// Imperial: maximum operational tempo and mass.
//------------------------------------------------------------------------------
rule rvltAge5Imperial
inactive
minInterval 90
{
   anwLogRuleTick("rvltAge5Imperial");
   if (gANWRevolutionCommanderEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() < cAge5)
   {
      return;
   }

   if (gRvltCivId == 1)        { btOffenseDefense = 0.65; btBiasInf = 1.0; btBiasCav = 0.2; btBiasArt = 0.8; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 2)   { btOffenseDefense = 0.95; btBiasInf = 1.0; btBiasCav = 0.55; btBiasArt = 0.85; cvMaxArmyPop = 180; }
   else if (gRvltCivId == 3)   { btOffenseDefense = 0.55; btBiasInf = 1.0; btBiasCav = 0.5; btBiasArt = 0.55; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 4)   { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = 0.7; btBiasArt = 0.85; cvMaxArmyPop = 160; }
   else if (gRvltCivId == 5)   { btOffenseDefense = 0.95; btBiasInf = 0.8; btBiasCav = 1.0; btBiasArt = 0.6; cvMaxArmyPop = 160; }
   else if (gRvltCivId == 6)   { btOffenseDefense = 0.85; btBiasInf = 1.0; btBiasCav = 0.7; btBiasArt = 0.75; cvMaxArmyPop = 160; }
   else if (gRvltCivId == 7)   { btOffenseDefense = 0.7; btBiasInf = 1.0; btBiasCav = 0.4; btBiasArt = 0.7; cvMaxArmyPop = 160; }
   else if (gRvltCivId == 8)   { btOffenseDefense = 0.95; btBiasInf = 0.9; btBiasCav = 1.0; btBiasArt = 0.7; cvMaxArmyPop = 165; }
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.95; btBiasInf = 1.0; btBiasCav = 0.5; btBiasArt = 0.55; cvMaxArmyPop = 170; }
   else if (gRvltCivId == 10)  { btOffenseDefense = 0.7; btBiasInf = 1.0; btBiasCav = 0.25; btBiasArt = 0.65; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 11)  { btOffenseDefense = 0.75; btBiasInf = 0.75; btBiasCav = 1.0; btBiasArt = 0.7; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 12)  { btOffenseDefense = 0.55; btBiasInf = 1.0; btBiasCav = 0.15; btBiasArt = 0.85; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 13)  { btOffenseDefense = 0.95; btBiasInf = 0.95; btBiasCav = 1.0; btBiasArt = 0.7; cvMaxArmyPop = 160; }
   else if (gRvltCivId == 14)  { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.65; btBiasArt = 0.85; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 15)  { btOffenseDefense = 0.95; btBiasInf = 0.75; btBiasCav = 1.0; btBiasArt = 0.6; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 16)  { btOffenseDefense = 0.95; btBiasInf = 1.0; btBiasCav = 0.65; btBiasArt = 1.0; cvMaxArmyPop = 165; }
   else if (gRvltCivId == 17)  { btOffenseDefense = 0.85; btBiasInf = 1.0; btBiasCav = 0.55; btBiasArt = 0.6; cvMaxArmyPop = 160; }
   else if (gRvltCivId == 18)  { btOffenseDefense = 0.95; btBiasInf = 0.6; btBiasCav = 1.0; btBiasArt = 0.3; cvMaxArmyPop = 150; }
   else if (gRvltCivId == 19)  { btOffenseDefense = 0.9; btBiasInf = 1.0; btBiasCav = 0.35; btBiasArt = 0.4; cvMaxArmyPop = 165; }
   else if (gRvltCivId == 20)  { btOffenseDefense = 0.95; btBiasInf = 0.7; btBiasCav = 1.0; btBiasArt = 0.45; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 21)  { btOffenseDefense = 1.0; btBiasInf = 1.0; btBiasCav = 0.1; btBiasArt = 0.05; cvMaxArmyPop = 165; }
   else if (gRvltCivId == 22)  { btOffenseDefense = 0.55; btBiasInf = 0.75; btBiasCav = 0.9; btBiasArt = 0.7; cvMaxArmyPop = 150; }
   else if (gRvltCivId == 23)  { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.75; btBiasArt = 0.65; cvMaxArmyPop = 160; }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btOffenseDefense = 0.95; btBiasInf = 0.8;  btBiasCav = 1.0;  btBiasArt = 0.6;  cvMaxArmyPop = 160; } // ANWArgentines
   else if (gRvltCivId == 25)  { btOffenseDefense = 0.95; btBiasInf = 0.75; btBiasCav = 1.0;  btBiasArt = 0.6;  cvMaxArmyPop = 155; } // ANWBarbary
   else if (gRvltCivId == 26)  { btOffenseDefense = 0.8;  btBiasInf = 1.0;  btBiasCav = 0.7;  btBiasArt = 0.85; cvMaxArmyPop = 160; } // ANWBrazil
   else if (gRvltCivId == 27)  { btOffenseDefense = 0.65; btBiasInf = 1.0;  btBiasCav = 0.2;  btBiasArt = 0.8;  cvMaxArmyPop = 155; } // ANWCanadians
   else if (gRvltCivId == 28)  { btOffenseDefense = 0.85; btBiasInf = 1.0;  btBiasCav = 0.8;  btBiasArt = 0.75; cvMaxArmyPop = 160; } // ANWChileans
   else if (gRvltCivId == 29)  { btOffenseDefense = 0.95; btBiasInf = 0.9;  btBiasCav = 1.0;  btBiasArt = 0.7;  cvMaxArmyPop = 165; } // ANWColumbians
   else if (gRvltCivId == 30)  { btOffenseDefense = 0.95; btBiasInf = 1.0;  btBiasCav = 0.65; btBiasArt = 1.0;  cvMaxArmyPop = 165; } // ANWEgyptians
   else if (gRvltCivId == 31)  { btOffenseDefense = 0.55; btBiasInf = 1.0;  btBiasCav = 0.15; btBiasArt = 0.85; cvMaxArmyPop = 155; } // ANWFinnish
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.95; btBiasInf = 1.0;  btBiasCav = 0.5;  btBiasArt = 0.55; cvMaxArmyPop = 170; } // ANWHaitians
   else if (gRvltCivId == 33)  { btOffenseDefense = 0.95; btBiasInf = 0.95; btBiasCav = 1.0;  btBiasArt = 0.7;  cvMaxArmyPop = 160; } // ANWHungarians
   else if (gRvltCivId == 34)  { btOffenseDefense = 0.7;  btBiasInf = 1.0;  btBiasCav = 0.25; btBiasArt = 0.65; cvMaxArmyPop = 155; } // ANWIndonesians
   else if (gRvltCivId == 35)  { btOffenseDefense = 1.0;  btBiasInf = 1.0;  btBiasCav = 0.1;  btBiasArt = 0.05; cvMaxArmyPop = 165; } // ANWMayans
   else if (gRvltCivId == 36)  { btOffenseDefense = 0.85; btBiasInf = 1.0;  btBiasCav = 0.6;  btBiasArt = 0.6;  cvMaxArmyPop = 160; } // ANWMexicans
   else if (gRvltCivId == 37)  { btOffenseDefense = 0.95; btBiasInf = 1.0;  btBiasCav = 0.85; btBiasArt = 0.9;  cvMaxArmyPop = 175; } // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btOffenseDefense = 0.7;  btBiasInf = 1.0;  btBiasCav = 0.4;  btBiasArt = 0.7;  cvMaxArmyPop = 160; } // ANWPeruvians
   else if (gRvltCivId == 39)  { btOffenseDefense = 0.95; btBiasInf = 1.0;  btBiasCav = 0.55; btBiasArt = 0.85; cvMaxArmyPop = 180; } // ANWRevFrance
   else if (gRvltCivId == 40)  { btOffenseDefense = 0.75; btBiasInf = 1.0;  btBiasCav = 0.65; btBiasArt = 0.85; cvMaxArmyPop = 155; } // ANWRomanians
   else if (gRvltCivId == 41)  { btOffenseDefense = 0.75; btBiasInf = 0.75; btBiasCav = 1.0;  btBiasArt = 0.7;  cvMaxArmyPop = 155; } // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.9;  btBiasArt = 0.65; cvMaxArmyPop = 160; } // ANWTexians
}

void anwEnableRevolutionCommanderRules(void)
{
   if (gANWRevolutionCommanderEnabled == false)
   {
      return;
   }

   xsEnableRule("rvltAge1Discovery");
   xsEnableRule("rvltAge2Colonial");
   xsEnableRule("rvltAge3Fortress");
   xsEnableRule("rvltAge4Industrial");
   xsEnableRule("rvltAge5Imperial");
}
