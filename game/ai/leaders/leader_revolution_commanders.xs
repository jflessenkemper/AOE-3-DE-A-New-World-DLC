//==============================================================================
/* leader_revolution_commanders.xs

   Bespoke commander personalities for the playable Revolution roster.

   Each civ gets a unique historical doctrine assigned in
   initLegendaryRevolutionCommander() and a bespoke per-age treatment
   applied through five rules below (Discovery -> Imperial). Civs with
   their own dedicated leader files (Napoleonic France, Americans,
   Mexicans -> Washington / Hidalgo / Napoleon) skip this dispatch.

   Civ ID legend (gRvltCivId):
       1  Canadians          - Isaac Brock, infantry-fort frontier
       2  RevolutionaryFrance- Robespierre, levee-en-masse conscription
       3  FrenchCanadians    - Papineau, Patriote militia + Iroquois levy
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

bool gLegendaryRevolutionCommanderEnabled = false;
int gRvltCivId = 0;

void initLegendaryRevolutionCommander(void)
{
   if (civIsRevolution() == false)
   {
      return;
   }

   string rvltName = kbGetCivName(cMyCiv);

   // These three civs are handled by their dedicated leader files.
   if ((rvltName == "RvltModNapoleonicFrance") || (rvltName == "RvltModAmericans") ||
       (rvltName == "RvltModMexicans"))
   {
      return;
   }

   // Default before the per-civ override.
   llSetBalancedPersonality();
   gRvltCivId = 0;

   if (rvltName == "RvltModCanadians")
   {
      llVerboseEcho("Legendary Leaders: activating Isaac Brock personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = -0.2;
      btBiasTrade = 0.25;
      btBiasNative = 0.1;          // Iroquois loyalist allies.
      llSetMilitaryFocus(0.85, -0.2, 0.35);
      // LL-BUILD-STYLE-BEGIN
      llUseCompactFortifiedCoreStyle(2, false);
      gLLEconomicDistanceMultiplier = 0.95;
      llSetBuildStrongpointProfile(2, 2, 2, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.86, 0.14, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 9;             // Frontier blockhouses.
      cvMaxArmyPop = 110;
      gRvltCivId = 1;
   }
   else if (rvltName == "RvltModRevolutionaryFrance")
   {
      llVerboseEcho("Legendary Leaders: activating Maximilien Robespierre personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.25;
      btBiasNative = -0.2;         // Levee-en-masse, no foreign auxiliaries.
      llSetMilitaryFocus(0.95, 0.0, 0.3);
      // LL-BUILD-STYLE-BEGIN
      llUseRepublicanLeveeStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(1, 1, 3, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 130;          // Conscription mass.
      gRvltCivId = 2;
   }
   else if (rvltName == "RvltModFrenchCanadians")
   {
      llVerboseEcho("Legendary Leaders: activating Louis-Joseph Papineau personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.25;
      btOffenseDefense = -0.05;
      btBiasTrade = 0.35;
      btBiasNative = 0.45;
      llSetMilitaryFocus(0.7, 0.0, 0.15);
      // LL-BUILD-STYLE-BEGIN
      llUseCivicMilitiaCenterStyle(1);
      gLLEconomicDistanceMultiplier = 1.05;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 110;
      gRvltCivId = 3;
   }
   else if (rvltName == "RvltModBrazil")
   {
      llVerboseEcho("Legendary Leaders: activating Pedro I personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.15;
      btOffenseDefense = 0.25;
      btBiasTrade = 0.35;
      btBiasNative = 0.15;
      llSetMilitaryFocus(0.55, 0.35, 0.45);
      // LL-BUILD-STYLE-BEGIN
      llUseDistributedEconomicNetworkStyle(2);
      gLLEconomicDistanceMultiplier = 1.35;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.8, 0.2, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 4;
   }
   else if (rvltName == "RvltModArgentines")
   {
      llVerboseEcho("Legendary Leaders: activating Jose de San Martin personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.15;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.4, 0.85, 0.2);  // Granadero a Caballo dominant.
      // LL-BUILD-STYLE-BEGIN
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.85;
      llSetBuildStrongpointProfile(1, 2, 3, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 3;
      cvMaxArmyPop = 115;
      gRvltCivId = 5;
   }
   else if (rvltName == "RvltModChileans")
   {
      llVerboseEcho("Legendary Leaders: activating Bernardo O'Higgins personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.1;
      btOffenseDefense = 0.35;
      btBiasTrade = 0.25;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.7, 0.35, 0.3);
      // LL-BUILD-STYLE-BEGIN
      llUseAndeanTerraceFortressStyle(2);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 2, 2, false);
      // Spec override: Chileans O'Higgins doctrine — see playstyle_spec.json
      gLLWallStrategy = cLLWallStrategyFortressRing;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 6;
   }
   else if (rvltName == "RvltModPeruvians")
   {
      llVerboseEcho("Legendary Leaders: activating Andres de Santa Cruz personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.3;
      btOffenseDefense = -0.1;
      btBiasTrade = 0.2;
      btBiasNative = 0.55;          // Quechua and Aymara levies.
      llSetMilitaryFocus(0.7, 0.05, 0.3);
      // LL-BUILD-STYLE-BEGIN
      llUseAndeanTerraceFortressStyle(3);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      // Spec override: Peruvians Santa Cruz doctrine — see playstyle_spec.json
      gLLWallStrategy = cLLWallStrategyFortressRing;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 115;
      gRvltCivId = 7;
   }
   else if (rvltName == "RvltModColumbians")
   {
      llVerboseEcho("Legendary Leaders: activating Simon Bolivar personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.15;
      btBiasNative = 0.2;
      llSetMilitaryFocus(0.45, 0.7, 0.3);  // Llanero horse-led.
      // LL-BUILD-STYLE-BEGIN
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(1, 1, 3, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.72, 0.28, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 120;
      gRvltCivId = 8;
   }
   else if (rvltName == "RvltModHaitians")
   {
      llVerboseEcho("Legendary Leaders: activating Toussaint Louverture personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = 0.15;
      btBiasNative = 0.65;
      llSetMilitaryFocus(0.85, 0.15, 0.15);
      // LL-BUILD-STYLE-BEGIN
      llUseJungleGuerrillaNetworkStyle(0);
      gLLEconomicDistanceMultiplier = 1.40;
      gLLTownCenterDistanceMultiplier = 1.40;
      // Spec override: Haitians Louverture doctrine — see playstyle_spec.json
      gLLWallStrategy = cLLWallStrategyChokepointSegments;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 125;
      gRvltCivId = 9;
   }
   else if (rvltName == "RvltModIndonesians")
   {
      llVerboseEcho("Legendary Leaders: activating Diponegoro personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.2;
      btOffenseDefense = -0.05;
      btBiasTrade = 0.3;
      btBiasNative = 0.55;
      llSetMilitaryFocus(0.8, -0.1, 0.2);
      // LL-BUILD-STYLE-BEGIN
      llUseShrineTradeNodeSpreadStyle(1);
      gLLEconomicDistanceMultiplier = 1.40;
      // Spec override: Indonesians Diponegoro doctrine — see playstyle_spec.json
      gLLWallStrategy = cLLWallStrategyChokepointSegments;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 115;
      gRvltCivId = 10;
   }
   else if (rvltName == "RvltModSouthAfricans")
   {
      llVerboseEcho("Legendary Leaders: activating Paul Kruger personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = 0.0;
      btBiasTrade = 0.5;
      btBiasNative = -0.1;
      llSetMilitaryFocus(0.4, 0.6, 0.25);  // Boer commando horse.
      // LL-BUILD-STYLE-BEGIN
      llUseNavalMercantileCompoundStyle(1);
      gLLEconomicDistanceMultiplier = 1.25;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 110;
      gRvltCivId = 11;
   }
   else if (rvltName == "RvltModFinnish")
   {
      llVerboseEcho("Legendary Leaders: activating Carl Gustaf Mannerheim personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.3;
      btOffenseDefense = -0.05;
      btBiasTrade = -0.05;
      btBiasNative = 0.15;          // Sami auxiliaries.
      llSetMilitaryFocus(0.85, -0.1, 0.4);
      // LL-BUILD-STYLE-BEGIN
      llUseCompactFortifiedCoreStyle(3, true);
      gLLHouseDistanceMultiplier = 0.80;
      llSetBuildStrongpointProfile(3, 2, 2, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.86, 0.14, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 9;              // Mannerheim Line.
      cvMaxArmyPop = 110;
      gRvltCivId = 12;
   }
   else if (rvltName == "RvltModHungarians")
   {
      llVerboseEcho("Legendary Leaders: activating Lajos Kossuth personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.15;
      btBiasNative = 0.0;
      llSetMilitaryFocus(0.55, 0.7, 0.25);  // Honved hussar wing.
      // LL-BUILD-STYLE-BEGIN
      llUseSteppeCavalryWedgeStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 3, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.74, 0.26, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 115;
      gRvltCivId = 13;
   }
   else if (rvltName == "RvltModRomanians")
   {
      llVerboseEcho("Legendary Leaders: activating Alexandru Ioan Cuza personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.25;
      btOffenseDefense = 0.05;
      btBiasTrade = 0.3;
      btBiasNative = 0.05;
      llSetMilitaryFocus(0.65, 0.3, 0.4);
      // LL-BUILD-STYLE-BEGIN
      llUseCivicMilitiaCenterStyle(2);
      gLLEconomicDistanceMultiplier = 1.10;
      llSetBuildStrongpointProfile(2, 1, 2, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 110;
      gRvltCivId = 14;
   }
   else if (rvltName == "RvltModBarbary")
   {
      llVerboseEcho("Legendary Leaders: activating Hayreddin Barbarossa personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.0;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.5;            // Corsair tribute.
      btBiasNative = 0.25;
      llSetMilitaryFocus(0.4, 0.65, 0.2);
      // LL-BUILD-STYLE-BEGIN
      llUseNavalMercantileCompoundStyle(2);
      gLLEconomicDistanceMultiplier = 1.20;
      llSetBuildStrongpointProfile(2, 2, 2, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 15;
   }
   else if (rvltName == "RvltModEgyptians")
   {
      llVerboseEcho("Legendary Leaders: activating Muhammad Ali Pasha personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.15;
      btOffenseDefense = 0.4;
      btBiasTrade = 0.35;
      btBiasNative = 0.0;
      llSetMilitaryFocus(0.7, 0.3, 0.55);   // Modern Nizam army.
      // LL-BUILD-STYLE-BEGIN
      llUseHighlandCitadelStyle(4);
      gLLHouseDistanceMultiplier = 0.75;
      llSetBuildStrongpointProfile(3, 3, 2, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 120;
      gRvltCivId = 16;
   }
   else if (rvltName == "RvltModCentralAmericans")
   {
      llVerboseEcho("Legendary Leaders: activating Francisco Morazan personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.1;
      btOffenseDefense = 0.3;
      btBiasTrade = 0.3;
      btBiasNative = 0.5;
      llSetMilitaryFocus(0.7, 0.25, 0.2);
      // LL-BUILD-STYLE-BEGIN
      llUseDistributedEconomicNetworkStyle(1);
      gLLEconomicDistanceMultiplier = 1.25;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.76, 0.24, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 17;
   }
   else if (rvltName == "RvltModBajaCalifornians")
   {
      // Manuel Pineda Muñoz — Mexican commander of the Baja garrisons during
      // the U.S. invasion of 1846-48 (defence of La Paz, San José del Cabo,
      // Mulegé). Coastal-presidio doctrine with mounted Californio militia
      // sweeping the peninsula's narrow corridor.
      llVerboseEcho("Legendary Leaders: activating Manuel Pineda Munoz personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.6;
      btBiasTrade = 0.2;
      btBiasNative = 0.15;
      llSetMilitaryFocus(0.3, 0.75, 0.15);  // Californio mounted militia.
      // LL-BUILD-STYLE-BEGIN
      llUseMobileFrontierScatterStyle(0);
      gLLHouseDistanceMultiplier = 1.40;
      gLLEconomicDistanceMultiplier = 1.50;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = false;
      cvMaxTowers = 3;
      cvMaxArmyPop = 110;
      gRvltCivId = 18;
   }
   else if (rvltName == "RvltModYucatan")
   {
      // Jacinto Pat — Maya batab and co-leader of the Caste War (Guerra de
      // Castas, 1847). Jungle guerrilla operating from the cenote-fed
      // limestone shelf, lifting Maya milicianos into the Yucatec interior.
      llVerboseEcho("Legendary Leaders: activating Jacinto Pat personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.05;
      btOffenseDefense = 0.45;
      btBiasTrade = 0.25;
      btBiasNative = 0.7;            // Maya levy.
      llSetMilitaryFocus(0.85, -0.1, 0.15);
      // LL-BUILD-STYLE-BEGIN
      llUseJungleGuerrillaNetworkStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      // Spec override: Yucatan Pat doctrine — see playstyle_spec.json
      gLLWallStrategy = cLLWallStrategyChokepointSegments;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 19;
   }
   else if (rvltName == "RvltModRioGrande")
   {
      llVerboseEcho("Legendary Leaders: activating Antonio Canales Rosillo personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.1;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.4, 0.75, 0.2);
      // LL-BUILD-STYLE-BEGIN
      llUseMobileFrontierScatterStyle(0);
      gLLHouseDistanceMultiplier = 1.35;
      gLLTownCenterDistanceMultiplier = 1.50;
      llSetBuildStrongpointProfile(1, 0, 2, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 115;
      gRvltCivId = 20;
   }
   else if (rvltName == "RvltModMayans")
   {
      llVerboseEcho("Legendary Leaders: activating Jacinto Canek personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = 0.1;
      btBiasNative = 0.85;
      llSetMilitaryFocus(0.95, -0.2, 0.0);
      // LL-BUILD-STYLE-BEGIN
      llUseJungleGuerrillaNetworkStyle(1);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 2, true);
      // Spec override: Mayans Canek doctrine — see playstyle_spec.json
      gLLWallStrategy = cLLWallStrategyChokepointSegments;
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 125;
      gRvltCivId = 21;
   }
   else if (rvltName == "RvltModCalifornians")
   {
      llVerboseEcho("Legendary Leaders: activating Mariano Guadalupe Vallejo personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = -0.15;
      btBiasTrade = 0.55;
      btBiasNative = 0.05;
      llSetMilitaryFocus(0.4, 0.55, 0.25);
      // LL-BUILD-STYLE-BEGIN
      llUseDistributedEconomicNetworkStyle(1);
      gLLHouseDistanceMultiplier = 1.15;
      gLLEconomicDistanceMultiplier = 1.40;
      llSetBuildStrongpointProfile(2, 1, 1, false);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 110;
      gRvltCivId = 22;
   }
   else if (rvltName == "RvltModTexians")
   {
      llVerboseEcho("Legendary Leaders: activating Sam Houston personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.25;
      btOffenseDefense = 0.0;
      btBiasTrade = 0.15;
      btBiasNative = 0.05;
      llSetMilitaryFocus(0.65, 0.45, 0.2);
      // LL-BUILD-STYLE-BEGIN
      llUseForwardOperationalLineStyle(0);
      gLLMilitaryDistanceMultiplier = 0.90;
      llSetBuildStrongpointProfile(2, 1, 3, true);
      // LL-BUILD-STYLE-END
      llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 115;
      gRvltCivId = 23;
   }
   // ── ANW revolution civs (24–42) ───────────────────────────────────────────
   else if (rvltName == "ANWArgentines")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Argentina San Martin personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.15;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.4, 0.85, 0.2);
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 3;
      cvMaxArmyPop = 115;
      gRvltCivId = 24;
   }
   else if (rvltName == "ANWBarbary")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Barbary Barbarossa personality.");
      llSetBalancedPersonality();
      btRushBoom = 0.0;
      btOffenseDefense = 0.55;
      btBiasTrade = 0.5;
      btBiasNative = 0.25;
      llSetMilitaryFocus(0.4, 0.65, 0.2);
      llSetLeaderTacticalDoctrine(0.72, 0.28, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 25;
   }
   else if (rvltName == "ANWBrazil")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Brazil Pedro II personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.15;
      btOffenseDefense = 0.25;
      btBiasTrade = 0.35;
      btBiasNative = 0.15;
      llSetMilitaryFocus(0.55, 0.35, 0.45);
      llSetLeaderTacticalDoctrine(0.8, 0.2, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 115;
      gRvltCivId = 26;
   }
   else if (rvltName == "ANWCanadians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Canadians Brock personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = -0.2;
      btBiasTrade = 0.25;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.85, -0.2, 0.35);
      llSetLeaderTacticalDoctrine(0.86, 0.14, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 9;
      cvMaxArmyPop = 110;
      gRvltCivId = 27;
   }
   else if (rvltName == "ANWChileans")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Chileans O'Higgins personality.");
      llSetAggressivePersonality();
      btRushBoom = -0.1;
      btOffenseDefense = 0.5;
      btBiasTrade = 0.2;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.7, 0.55, 0.3);
      llSetLeaderTacticalDoctrine(0.75, 0.25, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 28;
   }
   else if (rvltName == "ANWColumbians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Columbians Bolivar personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.15;
      btBiasNative = 0.2;
      llSetMilitaryFocus(0.45, 0.7, 0.3);
      llSetLeaderTacticalDoctrine(0.72, 0.28, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 120;
      gRvltCivId = 29;
   }
   else if (rvltName == "ANWEgyptians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Egyptians Muhammad Ali personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.15;
      btOffenseDefense = 0.4;
      btBiasTrade = 0.35;
      btBiasNative = 0.0;
      llSetMilitaryFocus(0.7, 0.3, 0.55);
      llSetLeaderTacticalDoctrine(0.78, 0.22, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 120;
      gRvltCivId = 30;
   }
   else if (rvltName == "ANWFinnish")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Finnish Mannerheim personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.3;
      btOffenseDefense = -0.05;
      btBiasTrade = -0.05;
      btBiasNative = 0.15;
      llSetMilitaryFocus(0.85, -0.1, 0.4);
      llSetLeaderTacticalDoctrine(0.86, 0.14, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 9;
      cvMaxArmyPop = 110;
      gRvltCivId = 31;
   }
   else if (rvltName == "ANWHaitians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Haitians Toussaint personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = 0.15;
      btBiasNative = 0.65;
      llSetMilitaryFocus(0.85, 0.15, 0.15);
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 125;
      gRvltCivId = 32;
   }
   else if (rvltName == "ANWHungarians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Hungarians Kossuth personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.65;
      btBiasTrade = 0.15;
      btBiasNative = 0.0;
      llSetMilitaryFocus(0.55, 0.7, 0.25);
      llSetLeaderTacticalDoctrine(0.74, 0.26, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 115;
      gRvltCivId = 33;
   }
   else if (rvltName == "ANWIndonesians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Indonesians Diponegoro personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.2;
      btOffenseDefense = -0.05;
      btBiasTrade = 0.3;
      btBiasNative = 0.55;
      llSetMilitaryFocus(0.8, -0.1, 0.2);
      llSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 115;
      gRvltCivId = 34;
   }
   else if (rvltName == "ANWMayans")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Mayans Caste War personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = 0.1;
      btBiasNative = 0.85;
      llSetMilitaryFocus(0.95, -0.2, 0.0);
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 125;
      gRvltCivId = 35;
   }
   else if (rvltName == "ANWMexicans")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Mexicans Hidalgo personality.");
      llSetBalancedPersonality();
      btRushBoom = -0.1;
      btOffenseDefense = 0.4;
      btBiasTrade = 0.1;
      btBiasNative = 0.2;
      llSetMilitaryFocus(0.75, 0.25, 0.3);
      llSetLeaderTacticalDoctrine(0.76, 0.24, 2, 4.0);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 36;
   }
   else if (rvltName == "ANWNapoleonicFrance")
   {
      llVerboseEcho("Legendary Leaders: activating ANW NapoleonicFrance Napoleon personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.1;
      btOffenseDefense = 0.75;
      btBiasTrade = 0.0;
      btBiasNative = -0.1;
      llSetMilitaryFocus(0.75, 0.55, 0.55);
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 135;
      gRvltCivId = 37;
   }
   else if (rvltName == "ANWPeruvians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Peruvians Santa Cruz personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.3;
      btOffenseDefense = -0.1;
      btBiasTrade = 0.2;
      btBiasNative = 0.55;
      llSetMilitaryFocus(0.7, 0.05, 0.3);
      llSetLeaderTacticalDoctrine(0.84, 0.16, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 115;
      gRvltCivId = 38;
   }
   else if (rvltName == "ANWRevFrance")
   {
      llVerboseEcho("Legendary Leaders: activating ANW RevFrance Robespierre personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.05;
      btOffenseDefense = 0.7;
      btBiasTrade = -0.25;
      btBiasNative = -0.2;
      llSetMilitaryFocus(0.95, 0.0, 0.3);
      llSetLeaderTacticalDoctrine(0.7, 0.3, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 4;
      cvMaxArmyPop = 130;
      gRvltCivId = 39;
   }
   else if (rvltName == "ANWRomanians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Romanians Cuza personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.25;
      btOffenseDefense = 0.05;
      btBiasTrade = 0.3;
      btBiasNative = 0.05;
      llSetMilitaryFocus(0.65, 0.3, 0.4);
      llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 6;
      cvMaxArmyPop = 110;
      gRvltCivId = 40;
   }
   else if (rvltName == "ANWSouthAfricans")
   {
      llVerboseEcho("Legendary Leaders: activating ANW SouthAfricans Kruger personality.");
      llSetDefensivePersonality();
      btRushBoom = -0.35;
      btOffenseDefense = 0.0;
      btBiasTrade = 0.5;
      btBiasNative = -0.1;
      llSetMilitaryFocus(0.4, 0.6, 0.25);
      llSetLeaderTacticalDoctrine(0.82, 0.18, 2, 4.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 7;
      cvMaxArmyPop = 110;
      gRvltCivId = 41;
   }
   else if (rvltName == "ANWTexians")
   {
      llVerboseEcho("Legendary Leaders: activating ANW Texians Sam Houston personality.");
      llSetAggressivePersonality();
      btRushBoom = 0.0;
      btOffenseDefense = 0.55;
      btBiasTrade = 0.1;
      btBiasNative = 0.1;
      llSetMilitaryFocus(0.6, 0.65, 0.25);
      llSetLeaderTacticalDoctrine(0.75, 0.25, 2, 3.5);
      cvOkToBuildForts = true;
      cvMaxTowers = 5;
      cvMaxArmyPop = 120;
      gRvltCivId = 42;
   }
   else
   {
      return;
   }

   debugLegendaryLeaders("revolution commander initialized for " + rvltName + " (civId " + gRvltCivId + ")");
   gLegendaryRevolutionCommanderEnabled = true;
   llLogLeaderState("revolution commander initialized for " + rvltName);
   // Replay probe: confirms which revolution commander block ran. The civ
   // name is the only stable key here (gLLLeaderKey is set later by
   // llAssignLeaderIdentity). gRvltCivId is the per-block ordinal.
   llProbe("meta.leader_init", "leader=rvlt_" + rvltName + " rvltCivId=" + gRvltCivId);
}

//------------------------------------------------------------------------------
// Discovery: per-civ economic / opening tilt.
//------------------------------------------------------------------------------
rule rvltAge1Discovery
inactive
minInterval 60
{
   llLogRuleTick("rvltAge1Discovery");
   if (gLegendaryRevolutionCommanderEnabled == false)
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
   llLogRuleTick("rvltAge2Colonial");
   if (gLegendaryRevolutionCommanderEnabled == false)
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
   else if (gRvltCivId == 2)   { btOffenseDefense = 0.75; btBiasInf = 0.95; btBiasCav = 0.2; btBiasArt = -0.1; llEnableForwardBaseStyle(); }
   // Papineau: Patriote militia + Iroquois screen.
   else if (gRvltCivId == 3)   { btOffenseDefense = 0.0; btBiasInf = 0.85; btBiasCav = 0.05; btBiasArt = -0.2; cvMinNumVills = 32; }
   // Pedro I: Imperial line + Hessian mercenary trickle.
   else if (gRvltCivId == 4)   { btOffenseDefense = 0.4; btBiasInf = 0.7; btBiasCav = 0.45; btBiasArt = 0.2; }
   // San Martin: Granadero a Caballo.
   else if (gRvltCivId == 5)   { btOffenseDefense = 0.7; btBiasInf = 0.4; btBiasCav = 0.85; btBiasArt = -0.2; llEnableForwardBaseStyle(); }
   // O'Higgins: balanced Republican infantry.
   else if (gRvltCivId == 6)   { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.4; btBiasArt = 0.0; }
   // Santa Cruz: Andean fort line, native muster.
   else if (gRvltCivId == 7)   { btOffenseDefense = -0.05; btBiasInf = 0.9; btBiasCav = 0.05; btBiasArt = -0.1; cvMinNumVills = 30; }
   // Bolivar: Llanero horse sweeps.
   else if (gRvltCivId == 8)   { btOffenseDefense = 0.7; btBiasInf = 0.5; btBiasCav = 0.85; btBiasArt = -0.1; llEnableForwardBaseStyle(); }
   // Toussaint: mass infantry insurrection.
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.1; btBiasArt = -0.3; llEnableForwardBaseStyle(); }
   // Diponegoro: Java War guerrilla and fortified kraton.
   else if (gRvltCivId == 10)  { btOffenseDefense = 0.0; btBiasInf = 0.9; btBiasCav = -0.1; btBiasArt = -0.2; cvMinNumVills = 30; }
   // Kruger: Boer commando trader-cavalry.
   else if (gRvltCivId == 11)  { btOffenseDefense = 0.05; btBiasInf = 0.4; btBiasCav = 0.7; btBiasArt = -0.1; cvMinNumVills = 30; }
   // Mannerheim: ski infantry behind frontier line.
   else if (gRvltCivId == 12)  { btOffenseDefense = -0.05; btBiasInf = 0.95; btBiasCav = -0.1; btBiasArt = 0.0; cvMinNumVills = 32; }
   // Kossuth: Honved hussar uprising.
   else if (gRvltCivId == 13)  { btOffenseDefense = 0.7; btBiasInf = 0.65; btBiasCav = 0.85; btBiasArt = -0.1; llEnableForwardBaseStyle(); }
   // Cuza: Danubian principalities consolidation.
   else if (gRvltCivId == 14)  { btOffenseDefense = 0.15; btBiasInf = 0.8; btBiasCav = 0.4; btBiasArt = 0.05; }
   // Barbarossa: corsair raid.
   else if (gRvltCivId == 15)  { btOffenseDefense = 0.7; btBiasInf = 0.45; btBiasCav = 0.75; btBiasArt = -0.2; llEnableForwardBaseStyle(); }
   // Muhammad Ali: Nizam-i Cedid line.
   else if (gRvltCivId == 16)  { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.35; btBiasArt = 0.1; }
   // Morazan: Federal Republic native muster.
   else if (gRvltCivId == 17)  { btOffenseDefense = 0.4; btBiasInf = 0.85; btBiasCav = 0.3; btBiasArt = -0.1; }
   // Alvarado: Californio horse raid.
   else if (gRvltCivId == 18)  { btOffenseDefense = 0.65; btBiasInf = 0.3; btBiasCav = 0.85; btBiasArt = -0.3; llEnableForwardBaseStyle(); }
   // Carrillo Puerto: Maya levy mass.
   else if (gRvltCivId == 19)  { btOffenseDefense = 0.55; btBiasInf = 0.95; btBiasCav = 0.05; btBiasArt = -0.3; }
   // Canales: Rio Grande horse.
   else if (gRvltCivId == 20)  { btOffenseDefense = 0.75; btBiasInf = 0.4; btBiasCav = 0.85; btBiasArt = -0.2; llEnableForwardBaseStyle(); }
   // Canek: indigenous insurrection mass.
   else if (gRvltCivId == 21)  { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = -0.2; btBiasArt = -0.4; llEnableForwardBaseStyle(); }
   // Vallejo: ranchero defense and trade.
   else if (gRvltCivId == 22)  { btOffenseDefense = -0.1; btBiasInf = 0.45; btBiasCav = 0.6; btBiasArt = -0.1; cvMinNumVills = 30; }
   // Houston: Republic of Texas militia.
   else if (gRvltCivId == 23)  { btOffenseDefense = 0.05; btBiasInf = 0.75; btBiasCav = 0.55; btBiasArt = -0.1; cvMinNumVills = 30; }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btOffenseDefense = 0.7;  btBiasInf = 0.4;  btBiasCav = 0.85; btBiasArt = -0.2; llEnableForwardBaseStyle(); }  // ANWArgentines
   else if (gRvltCivId == 25)  { btOffenseDefense = 0.65; btBiasInf = 0.45; btBiasCav = 0.75; btBiasArt = -0.2; llEnableForwardBaseStyle(); }  // ANWBarbary
   else if (gRvltCivId == 26)  { btOffenseDefense = 0.4;  btBiasInf = 0.7;  btBiasCav = 0.45; btBiasArt = 0.2;  }                              // ANWBrazil
   else if (gRvltCivId == 27)  { btOffenseDefense = -0.05; btBiasInf = 0.85; btBiasCav = -0.2; btBiasArt = -0.1; cvMinNumVills = 32; }          // ANWCanadians
   else if (gRvltCivId == 28)  { btOffenseDefense = 0.55; btBiasInf = 0.75; btBiasCav = 0.65; btBiasArt = 0.05; }                              // ANWChileans
   else if (gRvltCivId == 29)  { btOffenseDefense = 0.7;  btBiasInf = 0.5;  btBiasCav = 0.85; btBiasArt = -0.1; llEnableForwardBaseStyle(); }  // ANWColumbians
   else if (gRvltCivId == 30)  { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.35; btBiasArt = 0.1;  }                              // ANWEgyptians
   else if (gRvltCivId == 31)  { btOffenseDefense = -0.05; btBiasInf = 0.95; btBiasCav = -0.1; btBiasArt = 0.0;  cvMinNumVills = 32; }          // ANWFinnish
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.75; btBiasInf = 1.0;  btBiasCav = 0.1;  btBiasArt = -0.3; llEnableForwardBaseStyle(); }  // ANWHaitians
   else if (gRvltCivId == 33)  { btOffenseDefense = 0.7;  btBiasInf = 0.65; btBiasCav = 0.85; btBiasArt = -0.1; llEnableForwardBaseStyle(); }  // ANWHungarians
   else if (gRvltCivId == 34)  { btOffenseDefense = 0.0;  btBiasInf = 0.9;  btBiasCav = -0.1; btBiasArt = -0.2; cvMinNumVills = 30; }          // ANWIndonesians
   else if (gRvltCivId == 35)  { btOffenseDefense = 0.8;  btBiasInf = 1.0;  btBiasCav = -0.2; btBiasArt = -0.4; llEnableForwardBaseStyle(); }  // ANWMayans
   else if (gRvltCivId == 36)  { btOffenseDefense = 0.45; btBiasInf = 0.85; btBiasCav = 0.3;  btBiasArt = -0.1; }                              // ANWMexicans
   else if (gRvltCivId == 37)  { btOffenseDefense = 0.75; btBiasInf = 0.9;  btBiasCav = 0.6;  btBiasArt = 0.2;  llEnableForwardBaseStyle(); }  // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btOffenseDefense = -0.05; btBiasInf = 0.9;  btBiasCav = 0.05; btBiasArt = -0.1; cvMinNumVills = 30; }          // ANWPeruvians
   else if (gRvltCivId == 39)  { btOffenseDefense = 0.75; btBiasInf = 0.95; btBiasCav = 0.2;  btBiasArt = -0.1; llEnableForwardBaseStyle(); }  // ANWRevFrance
   else if (gRvltCivId == 40)  { btOffenseDefense = 0.15; btBiasInf = 0.8;  btBiasCav = 0.4;  btBiasArt = 0.05; }                              // ANWRomanians
   else if (gRvltCivId == 41)  { btOffenseDefense = 0.05; btBiasInf = 0.4;  btBiasCav = 0.7;  btBiasArt = -0.1; cvMinNumVills = 30; }          // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btOffenseDefense = 0.6;  btBiasInf = 0.65; btBiasCav = 0.8;  btBiasArt = -0.1; llEnableForwardBaseStyle(); }  // ANWTexians
}

//------------------------------------------------------------------------------
// Fortress: signature doctrine assembles.
//------------------------------------------------------------------------------
rule rvltAge3Fortress
inactive
minInterval 55
{
   llLogRuleTick("rvltAge3Fortress");
   if (gLegendaryRevolutionCommanderEnabled == false)
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
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.85; btBiasInf = 1.0; btBiasCav = 0.3; btBiasArt = 0.2; cvMaxArmyPop = 140; llEnableForwardBaseStyle(); }
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
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.85; btBiasInf = 1.0;  btBiasCav = 0.3;  btBiasArt = 0.2;  cvMaxArmyPop = 140; llEnableForwardBaseStyle(); } // ANWHaitians
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
   llLogRuleTick("rvltAge4Industrial");
   if (gLegendaryRevolutionCommanderEnabled == false)
   {
      xsDisableSelf();
      return;
   }

   if (kbGetAge() != cAge4)
   {
      return;
   }

   if (gRvltCivId == 1)        { btOffenseDefense = 0.5; btBiasInf = 1.0; btBiasCav = 0.1; btBiasArt = 0.65; cvMaxArmyPop = 140; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 2)   { btOffenseDefense = 0.9; btBiasInf = 1.0; btBiasCav = 0.5; btBiasArt = 0.7; cvMaxArmyPop = 165; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 3)   { btOffenseDefense = 0.45; btBiasInf = 1.0; btBiasCav = 0.4; btBiasArt = 0.45; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 4)   { btOffenseDefense = 0.7; btBiasInf = 1.0; btBiasCav = 0.65; btBiasArt = 0.75; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 5)   { btOffenseDefense = 0.85; btBiasInf = 0.7; btBiasCav = 1.0; btBiasArt = 0.45; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 6)   { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.65; btBiasArt = 0.6; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 7)   { btOffenseDefense = 0.55; btBiasInf = 1.0; btBiasCav = 0.3; btBiasArt = 0.6; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 8)   { btOffenseDefense = 0.85; btBiasInf = 0.8; btBiasCav = 1.0; btBiasArt = 0.55; cvMaxArmyPop = 150; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 9)   { btOffenseDefense = 0.9; btBiasInf = 1.0; btBiasCav = 0.4; btBiasArt = 0.4; cvMaxArmyPop = 155; }
   else if (gRvltCivId == 10)  { btOffenseDefense = 0.55; btBiasInf = 1.0; btBiasCav = 0.15; btBiasArt = 0.5; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 11)  { btOffenseDefense = 0.6; btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.55; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 12)  { btOffenseDefense = 0.4; btBiasInf = 1.0; btBiasCav = 0.05; btBiasArt = 0.7; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 13)  { btOffenseDefense = 0.85; btBiasInf = 0.85; btBiasCav = 1.0; btBiasArt = 0.55; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 14)  { btOffenseDefense = 0.6; btBiasInf = 1.0; btBiasCav = 0.55; btBiasArt = 0.7; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 15)  { btOffenseDefense = 0.85; btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.45; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 16)  { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = 0.55; btBiasArt = 0.85; cvMaxArmyPop = 150; llEnableForwardBaseStyle(); }
   else if (gRvltCivId == 17)  { btOffenseDefense = 0.75; btBiasInf = 1.0; btBiasCav = 0.45; btBiasArt = 0.45; cvMaxArmyPop = 145; }
   else if (gRvltCivId == 18)  { btOffenseDefense = 0.85; btBiasInf = 0.5; btBiasCav = 1.0; btBiasArt = 0.15; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 19)  { btOffenseDefense = 0.8; btBiasInf = 1.0; btBiasCav = 0.25; btBiasArt = 0.2; cvMaxArmyPop = 150; }
   else if (gRvltCivId == 20)  { btOffenseDefense = 0.9; btBiasInf = 0.6; btBiasCav = 1.0; btBiasArt = 0.3; cvMaxArmyPop = 140; }
   else if (gRvltCivId == 21)  { btOffenseDefense = 0.95; btBiasInf = 1.0; btBiasCav = 0.0; btBiasArt = -0.1; cvMaxArmyPop = 150; }
   else if (gRvltCivId == 22)  { btOffenseDefense = 0.4; btBiasInf = 0.65; btBiasCav = 0.8; btBiasArt = 0.55; cvMaxArmyPop = 135; }
   else if (gRvltCivId == 23)  { btOffenseDefense = 0.6; btBiasInf = 1.0; btBiasCav = 0.7; btBiasArt = 0.5; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); }
   // ANW (24–42)
   else if (gRvltCivId == 24)  { btOffenseDefense = 0.85; btBiasInf = 0.7;  btBiasCav = 1.0;  btBiasArt = 0.45; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); } // ANWArgentines
   else if (gRvltCivId == 25)  { btOffenseDefense = 0.85; btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.45; cvMaxArmyPop = 140; }                             // ANWBarbary
   else if (gRvltCivId == 26)  { btOffenseDefense = 0.7;  btBiasInf = 1.0;  btBiasCav = 0.65; btBiasArt = 0.75; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); } // ANWBrazil
   else if (gRvltCivId == 27)  { btOffenseDefense = 0.5;  btBiasInf = 1.0;  btBiasCav = 0.1;  btBiasArt = 0.65; cvMaxArmyPop = 140; llEnableForwardBaseStyle(); } // ANWCanadians
   else if (gRvltCivId == 28)  { btOffenseDefense = 0.75; btBiasInf = 1.0;  btBiasCav = 0.75; btBiasArt = 0.6;  cvMaxArmyPop = 145; }                             // ANWChileans
   else if (gRvltCivId == 29)  { btOffenseDefense = 0.85; btBiasInf = 0.8;  btBiasCav = 1.0;  btBiasArt = 0.55; cvMaxArmyPop = 150; llEnableForwardBaseStyle(); } // ANWColumbians
   else if (gRvltCivId == 30)  { btOffenseDefense = 0.8;  btBiasInf = 1.0;  btBiasCav = 0.55; btBiasArt = 0.85; cvMaxArmyPop = 150; llEnableForwardBaseStyle(); } // ANWEgyptians
   else if (gRvltCivId == 31)  { btOffenseDefense = 0.4;  btBiasInf = 1.0;  btBiasCav = 0.05; btBiasArt = 0.7;  cvMaxArmyPop = 140; }                             // ANWFinnish
   else if (gRvltCivId == 32)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.4;  btBiasArt = 0.4;  cvMaxArmyPop = 155; }                             // ANWHaitians
   else if (gRvltCivId == 33)  { btOffenseDefense = 0.85; btBiasInf = 0.85; btBiasCav = 1.0;  btBiasArt = 0.55; cvMaxArmyPop = 145; }                             // ANWHungarians
   else if (gRvltCivId == 34)  { btOffenseDefense = 0.55; btBiasInf = 1.0;  btBiasCav = 0.15; btBiasArt = 0.5;  cvMaxArmyPop = 140; }                             // ANWIndonesians
   else if (gRvltCivId == 35)  { btOffenseDefense = 0.95; btBiasInf = 1.0;  btBiasCav = 0.0;  btBiasArt = -0.1; cvMaxArmyPop = 150; }                             // ANWMayans
   else if (gRvltCivId == 36)  { btOffenseDefense = 0.7;  btBiasInf = 1.0;  btBiasCav = 0.5;  btBiasArt = 0.45; cvMaxArmyPop = 145; }                             // ANWMexicans
   else if (gRvltCivId == 37)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.8;  btBiasArt = 0.8;  cvMaxArmyPop = 160; llEnableForwardBaseStyle(); } // ANWNapoleonicFrance
   else if (gRvltCivId == 38)  { btOffenseDefense = 0.55; btBiasInf = 1.0;  btBiasCav = 0.3;  btBiasArt = 0.6;  cvMaxArmyPop = 145; llEnableForwardBaseStyle(); } // ANWPeruvians
   else if (gRvltCivId == 39)  { btOffenseDefense = 0.9;  btBiasInf = 1.0;  btBiasCav = 0.5;  btBiasArt = 0.7;  cvMaxArmyPop = 165; llEnableForwardBaseStyle(); } // ANWRevFrance
   else if (gRvltCivId == 40)  { btOffenseDefense = 0.6;  btBiasInf = 1.0;  btBiasCav = 0.55; btBiasArt = 0.7;  cvMaxArmyPop = 140; }                             // ANWRomanians
   else if (gRvltCivId == 41)  { btOffenseDefense = 0.6;  btBiasInf = 0.65; btBiasCav = 0.95; btBiasArt = 0.55; cvMaxArmyPop = 140; }                             // ANWSouthAfricans
   else if (gRvltCivId == 42)  { btOffenseDefense = 0.75; btBiasInf = 0.9;  btBiasCav = 0.9;  btBiasArt = 0.45; cvMaxArmyPop = 145; llEnableForwardBaseStyle(); } // ANWTexians
}

//------------------------------------------------------------------------------
// Imperial: maximum operational tempo and mass.
//------------------------------------------------------------------------------
rule rvltAge5Imperial
inactive
minInterval 90
{
   llLogRuleTick("rvltAge5Imperial");
   if (gLegendaryRevolutionCommanderEnabled == false)
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

void enableLegendaryRevolutionCommanderRules(void)
{
   if (gLegendaryRevolutionCommanderEnabled == false)
   {
      return;
   }

   xsEnableRule("rvltAge1Discovery");
   xsEnableRule("rvltAge2Colonial");
   xsEnableRule("rvltAge3Fortress");
   xsEnableRule("rvltAge4Industrial");
   xsEnableRule("rvltAge5Imperial");
}
