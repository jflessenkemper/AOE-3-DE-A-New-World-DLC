//==============================================================================
/* aiEliteTactics.xs

   Keeps non-elite troops screening elite units and heroes while under pressure.
   During active assaults, standard troops lead, elites follow close behind, and
   the explorer stays behind the elite line. If the explorer falls, elites break
   contact and the AI immediately tries to ransom the leader back from home.
*/
//==============================================================================

extern int gANWEliteGuardPlanID = -1;
extern int gANWEliteGuardAnchorUnitID = -1;
extern int gANWEliteSupportPlanID = -1;
extern int gANWEliteSupportAttackPlanID = -1;
extern int gANWEliteSupportLastRefreshTime = -1;
extern int gANWExplorerEscortPlanID = -1;
extern int gANWExplorerEscortAttackPlanID = -1;
extern int gANWExplorerEscortLastRefreshTime = -1;
float gANWExplorerProtectionOverride = -1.0;
float gANWDecapitationOverride = -1.0;
int gANWExplorerEscortBonus = 0;
float gANWExplorerRearOffsetBonus = 0.0;

// Elite-unit proto registry — populated once at init by anwInitEliteProtoIDs().
// Holds cUnitType* constants and kbGetProtoUnitID()-resolved IDs for the
// current civ's unique units. Max 12 slots covers the widest ANW civ (ANWAztecs:5,
// ANWArgentines:5+). -1 entries are skipped. Declared here (top of file) so they
// precede first use in anwInitEliteProtoIDs/anwIsEliteUnit (XS needs decl-before-use).
extern int gANWEliteProtoIDsArrayID = -1;
extern int gANWEliteProtoCount = 0;
const int cANWEliteProtoMax = 12;

//==============================================================================
/* anwInitEliteProtoIDs — called once at rout-system boot (inside the
   gANWAiRoutBootMarkerEmitted==0 guard in anwAiRoutMonitor) after kb is
   ready. Reads kbGetCivName(cMyCiv) and pushes all confirmed unique-unit type
   IDs for the current ANW civ into gANWEliteProtoIDsArrayID.

   cUnitType* constants are pushed directly (engine integers).
   Proto strings are resolved via kbGetProtoUnitID() and pushed only if >= 0
   (guard against missing protos — never push -1).

   Civs where doc-04 marks units as UNRESOLVED get no entry for that unit;
   those civs may still get other resolved entries and degrade gracefully.

   Base-game fallback block at the bottom handles the 8 original civs so this
   file stays backward-compatible with non-ANW games. */
//==============================================================================
void anwInitEliteProtoIDs(void)
{
   // Create the array once.
   if (gANWEliteProtoIDsArrayID < 0)
   {
      gANWEliteProtoIDsArrayID = xsArrayCreateInt(cANWEliteProtoMax, -1, "LL elite proto ids");
   }
   gANWEliteProtoCount = 0;

   string civName = kbGetCivName(cMyCiv);

   // ── Helper macro-pattern: push a type id if valid ──────────────────────
   // (XS has no macros; the push logic is inlined at each site below.)

   if (civName == "ANWArgentines")
   {
      // deREVGranadero, Lancer, Rodelero, WarDog (Gatling Gun = xpGatlingGun proto)
      int pid0 = kbGetProtoUnitID("deREVGranadero");
      if (pid0 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid0); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRodelero);     gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeWarDog);       gANWEliteProtoCount++;
      int pid1 = kbGetProtoUnitID("xpGatlingGun");
      if (pid1 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid1); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWAztecs")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpJaguarKnight);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpArrowKnight);   gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpSkullKnight);   gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpPumaMan);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpMacehualtin);   gANWEliteProtoCount++;
   }
   else if (civName == "ANWBarbary")
   {
      int pid2 = kbGetProtoUnitID("deREVBarbaryWarrior");
      if (pid2 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid2); gANWEliteProtoCount++; }
      int pid3 = kbGetProtoUnitID("deBarbaryCavalry");
      if (pid3 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid3); gANWEliteProtoCount++; }
      int pid4 = kbGetProtoUnitID("deBedouinHorseArcher");
      if (pid4 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid4); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeGreatBombard);    gANWEliteProtoCount++;
      // Corsair Marksman (deAllegianceBarbaryMarksman) — confirmed in techtreemods unittypes
      int pid5 = kbGetProtoUnitID("deAllegianceBarbaryMarksman");
      if (pid5 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid5); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWBrazil")
   {
      // Voluntario actual spawned proto UNRESOLVED — TODO: fill when proto string confirmed
      int pid6 = kbGetProtoUnitID("xpGatlingGun");
      if (pid6 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid6); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);          gANWEliteProtoCount++;
   }
   else if (civName == "ANWBritish")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLongbowman);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRocket);          gANWEliteProtoCount++;
      int pid7 = kbGetProtoUnitID("deRanger");
      if (pid7 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid7); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWCanadians")
   {
      int pid8 = kbGetProtoUnitID("deRanger");
      if (pid8 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid8); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRocket);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCuirassier);      gANWEliteProtoCount++;
      // Métis Pathfinder/Voyageur are Coureur reskins — not independently testable via kbUnitIsType
      // TODO: no distinct combat proto available per doc-04
   }
   else if (civName == "ANWChileans")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRodelero);        gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeWarDog);          gANWEliteProtoCount++;
      int pid9 = kbGetProtoUnitID("xpGatlingGun");
      if (pid9 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid9); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWChinese")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypChuKoNu);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypMeteorHammer);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypChangdao);      gANWEliteProtoCount++;
      // ypFlamethrower — no cUnitTypeypFlamethrower constant in AI source; proto string likely correct
      // but unverified in XS. TODO: replace with cUnitType constant when confirmed.
      int pid10 = kbGetProtoUnitID("ypFlamethrower");
      if (pid10 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid10); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWColumbians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRodelero);        gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeWarDog);          gANWEliteProtoCount++;
      int pid11 = kbGetProtoUnitID("deREVLlanero");
      if (pid11 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid11); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWDutch")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRuyter);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeHalberdier);      gANWEliteProtoCount++;
   }
   else if (civName == "ANWEgyptians")
   {
      int pid12 = kbGetProtoUnitID("MercMameluke");
      if (pid12 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid12); gANWEliteProtoCount++; }
      int pid13 = kbGetProtoUnitID("deDeli");
      if (pid13 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid13); gANWEliteProtoCount++; }
      int pid14 = kbGetProtoUnitID("deHumbaraci");
      if (pid14 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid14); gANWEliteProtoCount++; }
      int pid15 = kbGetProtoUnitID("deAzap");
      if (pid15 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid15); gANWEliteProtoCount++; }
      // Khevite Fusilier UNRESOLVED — no proto token found in repo data. TODO.
   }
   else if (civName == "ANWEthiopians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeOromoWarrior);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeShotelWarrior); gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeRifleman);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeSebastopolMortar); gANWEliteProtoCount++;
   }
   else if (civName == "ANWFinnish")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeFinnishRider);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeGrenadier);       gANWEliteProtoCount++;
      // Karelian Jaeger = Skirmisher reskin, not uniquely distinguishable — not added per doc-04
   }
   else if (civName == "ANWFrench")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCuirassier);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeSkirmisher);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCoureur);         gANWEliteProtoCount++;
   }
   else if (civName == "ANWGermans")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeUhlan);           gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeWarWagon);        gANWEliteProtoCount++;
      // Doppelsoldner: no confirmed cUnitTypedeDoppelsoldner in AI files. TODO.
   }
   else if (civName == "ANWHaitians")
   {
      // Maroon cUnitType UNRESOLVED — deMaroon plausible but unconfirmed. TODO.
      int pid16 = kbGetProtoUnitID("SaloonPirate");
      if (pid16 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid16); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWHaudenosaunee")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpWarRifle);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpAenna);         gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpMantlet);       gANWEliteProtoCount++;
   }
   else if (civName == "ANWHausa")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeFulaWarrior);   gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeRifleman);      gANWEliteProtoCount++;
      // Lifidi Knight: proto deLifidiKnight plausible but UNRESOLVED in repo data. TODO.
   }
   else if (civName == "ANWHungarians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeHussar);          gANWEliteProtoCount++;
      int pid17 = kbGetProtoUnitID("deNMPandour");
      if (pid17 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid17); gANWEliteProtoCount++; }
      int pid18 = kbGetProtoUnitID("deMercPandour");
      if (pid18 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid18); gANWEliteProtoCount++; }
      // Grenzer and Hajduk are spawned outpost units, not trainable protos. UNRESOLVED.
   }
   else if (civName == "ANWInca")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeBolasWarrior);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeIncaRunner);    gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeSpearmanLevy);  gANWEliteProtoCount++;
      // Huaraca: proto deHuaraca likely but no cUnitType confirmed. TODO.
   }
   else if (civName == "ANWIndians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypUrumi);         gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypSepoy);         gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypZamburak);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypHowdah);        gANWEliteProtoCount++;
   }
   else if (civName == "ANWIndonesians")
   {
      int pid19 = kbGetProtoUnitID("deREVJavaSpearman");
      if (pid19 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid19); gANWEliteProtoCount++; }
      int pid20 = kbGetProtoUnitID("deREVCetbang");
      if (pid20 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid20); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRuyter);          gANWEliteProtoCount++;
   }
   else if (civName == "ANWItalians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeBersagliere);   gANWEliteProtoCount++;
      int pid21 = kbGetProtoUnitID("dePapalGuard");
      if (pid21 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid21); gANWEliteProtoCount++; }
      // Papal Lancer: no proto token found in any data file. UNRESOLVED. TODO.
   }
   else if (civName == "ANWJapanese")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypYumi);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypNaginataRider); gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeypKensei);        gANWEliteProtoCount++;
      // Flaming Arrow: artillery unit, proto UNRESOLVED. TODO.
   }
   else if (civName == "ANWLakota")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpWarRifle);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpAxeRider);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpDogSoldier);    gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpRifleRider);    gANWEliteProtoCount++;
   }
   else if (civName == "ANWMaltese")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeHospitaller);   gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeMalteseGun);    gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedePavisier);      gANWEliteProtoCount++;
   }
   else if (civName == "ANWMayans")
   {
      int pid22 = kbGetProtoUnitID("deNatHolcanJavelineer");
      if (pid22 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid22); gANWEliteProtoCount++; }
      int pid23 = kbGetProtoUnitID("deREVCruzobInfantry");
      if (pid23 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid23); gANWEliteProtoCount++; }
      int pid24 = kbGetProtoUnitID("deInsurgente");
      if (pid24 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid24); gANWEliteProtoCount++; }
      // Cruzob Avenger distinct proto UNRESOLVED — icon token only. TODO.
   }
   else if (civName == "ANWMexicans")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedePadre);         gANWEliteProtoCount++;
      int pid25 = kbGetProtoUnitID("deInsurgente");
      if (pid25 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid25); gANWEliteProtoCount++; }
      int pid26 = kbGetProtoUnitID("deEmboscador");
      if (pid26 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid26); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeSoldado);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeChinaco);       gANWEliteProtoCount++;
   }
   else if (civName == "ANWNapoleonicFrance")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCuirassier);      gANWEliteProtoCount++;
      int pid27 = kbGetProtoUnitID("deInsurgente");
      if (pid27 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid27); gANWEliteProtoCount++; }
      // Old Guard is a Grenadier reskin (no unique proto); use cUnitTypeGrenadier
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeGrenadier);       gANWEliteProtoCount++;
   }
   else if (civName == "ANWOttomans")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeJanissary);       gANWEliteProtoCount++;
      int pid28 = kbGetProtoUnitID("Spahi");
      if (pid28 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid28); gANWEliteProtoCount++; }
      int pid29 = kbGetProtoUnitID("AbusGun");
      if (pid29 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid29); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeGreatBombard);    gANWEliteProtoCount++;
   }
   else if (civName == "ANWPeruvians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRodelero);        gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeWarDog);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeChasqui);       gANWEliteProtoCount++;
   }
   else if (civName == "ANWPortuguese")
   {
      int pid30 = kbGetProtoUnitID("Cacadore");
      if (pid30 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid30); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeOrganGun);        gANWEliteProtoCount++;
   }
   else if (civName == "ANWRevFrance")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCuirassier);      gANWEliteProtoCount++;
      int pid31 = kbGetProtoUnitID("deInsurgente");
      if (pid31 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid31); gANWEliteProtoCount++; }
      // Sans Culottes = Coureur (renamed via SetName) — use cUnitTypeCoureur
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCoureur);         gANWEliteProtoCount++;
   }
   else if (civName == "ANWRomanians")
   {
      // Rosior Dragoon = Dragoon (reskin); Dorobant = xpColonialMilitia (reskin)
      // No unique protos — use base types as approximate per doc-04.
      int pid32 = kbGetProtoUnitID("Dragoon");
      if (pid32 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid32); gANWEliteProtoCount++; }
      int pid33 = kbGetProtoUnitID("xpColonialMilitia");
      if (pid33 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid33); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWRussians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeStrelet);         gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);          gANWEliteProtoCount++;
      int pid34 = kbGetProtoUnitID("Oprichnik");
      if (pid34 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid34); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWSouthAfricans")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRuyter);          gANWEliteProtoCount++;
      int pid35 = kbGetProtoUnitID("deREVStarTrekWagon");
      if (pid35 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid35); gANWEliteProtoCount++; }
   }
   else if (civName == "ANWSpanish")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRodelero);        gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLancer);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeWarDog);          gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeMissionary);      gANWEliteProtoCount++;
   }
   else if (civName == "ANWSwedes")
   {
      // deCarolean confirmed in techtreemods; no cUnitTypedeCarolean in AI source — use kbGetProtoUnitID
      int pid36 = kbGetProtoUnitID("deCarolean");
      if (pid36 >= 0) { xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, pid36); gANWEliteProtoCount++; }
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeFinnishRider);  gANWEliteProtoCount++;
      // Leather Cannon (deLeatherCannons) UNRESOLVED as cUnitType. TODO.
   }
   else if (civName == "ANWTexians")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeMinuteman);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeStateMilitia);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeRegular);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeRifleman);      gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeChinaco);       gANWEliteProtoCount++;
   }
   else if (civName == "ANWUSA")
   {
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeMinuteman);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeStateMilitia);  gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeRegular);       gANWEliteProtoCount++;
      xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypedeRifleman);      gANWEliteProtoCount++;
   }
   else
   {
      // Base-game fallback — handles the 8 original civs (non-ANW games).
      // switch(cMyCiv) is valid here because these are true cCiv* integer constants.
      switch (cMyCiv)
      {
         case cCivBritish:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeLongbowman); gANWEliteProtoCount++;
            break;
         }
         case cCivFrench:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeCuirassier); gANWEliteProtoCount++;
            break;
         }
         case cCivGermans:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeUhlan); gANWEliteProtoCount++;
            break;
         }
         case cCivRussians:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeStrelet); gANWEliteProtoCount++;
            break;
         }
         case cCivOttomans:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeJanissary); gANWEliteProtoCount++;
            break;
         }
         case cCivDutch:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRuyter); gANWEliteProtoCount++;
            break;
         }
         case cCivSpanish:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypeRodelero); gANWEliteProtoCount++;
            break;
         }
         case cCivXPAztec:
         {
            xsArraySetInt(gANWEliteProtoIDsArrayID, gANWEliteProtoCount, cUnitTypexpJaguarKnight); gANWEliteProtoCount++;
            break;
         }
      }
   }

   anwProbe("rout.elite_protos_init", "civ=" + civName + " count=" + gANWEliteProtoCount);
}

//==============================================================================
/* anwIsEliteUnit — predicate for "elite" land-military units used by the
   screening logic in this file. Loops gANWEliteProtoIDsArrayID (populated by
   anwInitEliteProtoIDs at boot) and returns true if the unit matches any entry.
   Returns false for unitID < 0, empty array, or no match — degrades safely to
   the 25% rout path. Heroes are counted separately by callers. */
//==============================================================================
bool anwIsEliteUnit(int unitID = -1)
{
   if (unitID < 0)
   {
      return (false);
   }

   if ((gANWEliteProtoIDsArrayID < 0) || (gANWEliteProtoCount <= 0))
   {
      return (false);
   }

   int i = 0;
   for (i = 0; < gANWEliteProtoCount)
   {
      int typeID = xsArrayGetInt(gANWEliteProtoIDsArrayID, i);
      if (typeID >= 0)
      {
         if (kbUnitIsType(unitID, typeID) == true)
         {
            return (true);
         }
      }
   }

   return (false);
}

float anwClamp01(float value = 0.0)
{
   if (value < 0.0)
   {
      return (0.0);
   }

   if (value > 1.0)
   {
      return (1.0);
   }

   return (value);
}

void anwSetLeaderTacticalDoctrine(float protectionOverride = -1.0, float decapitationOverride = -1.0,
   int escortBonus = 0, float rearOffsetBonus = 0.0)
{
   gANWExplorerProtectionOverride = protectionOverride;
   gANWDecapitationOverride = decapitationOverride;
   gANWExplorerEscortBonus = escortBonus;
   gANWExplorerRearOffsetBonus = rearOffsetBonus;
   anwProbe("event.elite.doctrine",
      "protect=" + protectionOverride + " decap=" + decapitationOverride +
      " escortBonus=" + escortBonus + " rearOffset=" + rearOffsetBonus);
}

int anwGetPlaystyleBucket(void)
{
   if (btOffenseDefense >= 0.35)
   {
      return (2);
   }

   if (btOffenseDefense <= -0.25)
   {
      return (0);
   }

   return (1);
}

float anwGetExplorerProtectionBias(void)
{
   if (gANWExplorerProtectionOverride >= 0.0)
   {
      return (anwClamp01(gANWExplorerProtectionOverride));
   }

   float protectionBias = 0.55 - (btOffenseDefense * 0.35) + (btBiasInf * 0.12) + (btBiasArt * 0.10) -
      (btBiasCav * 0.14) - (btBiasNative * 0.06);

   if (anwGetPlaystyleBucket() == 0)
   {
      protectionBias = protectionBias + 0.12;
   }
   else if (anwGetPlaystyleBucket() == 2)
   {
      protectionBias = protectionBias - 0.08;
   }

   return (anwClamp01(protectionBias));
}

float anwGetDecapitationBias(void)
{
   if (gANWDecapitationOverride >= 0.0)
   {
      return (anwClamp01(gANWDecapitationOverride));
   }

   float decapitationBias = 0.20 + (btOffenseDefense * 0.38) + (btBiasCav * 0.24) + (btBiasNative * 0.10) -
      (btBiasArt * 0.12) - (btBiasInf * 0.08);

   if (anwGetPlaystyleBucket() == 2)
   {
      decapitationBias = decapitationBias + 0.10;
   }
   else if (anwGetPlaystyleBucket() == 0)
   {
      decapitationBias = decapitationBias - 0.14;
   }

   return (anwClamp01(decapitationBias));
}

vector anwGetEliteRetreatPoint(void)
{
   int mainBaseID = kbBaseGetMainID(cMyID);
   vector retreatPoint = kbBaseGetMilitaryGatherPoint(cMyID, mainBaseID);
   if (retreatPoint == cInvalidVector)
   {
      retreatPoint = kbBaseGetLocation(cMyID, mainBaseID);
   }

   return (retreatPoint);
}

vector anwGetAssaultOffsetPoint(vector gatherPoint = cInvalidVector, vector targetPoint = cInvalidVector, float offset = 0.0)
{
   if (targetPoint == cInvalidVector)
   {
      return (cInvalidVector);
   }

   if (gatherPoint == cInvalidVector)
   {
      gatherPoint = anwGetEliteRetreatPoint();
   }

   if ((gatherPoint == cInvalidVector) || (distance(gatherPoint, targetPoint) < 4.0) || (offset <= 0.0))
   {
      return (targetPoint);
   }

   return (targetPoint - (xsVectorNormalize(targetPoint - gatherPoint) * offset));
}

int anwGetNearbyEnemyPressureCount(vector location = cInvalidVector, float radius = 28.0)
{
   if ((location == cInvalidVector) || (radius <= 0.0))
   {
      return (0);
   }

   int enemyQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cPlayerRelationEnemyNotGaia,
      cUnitStateAlive, location, radius);
   return (kbUnitQueryExecute(enemyQueryID));
}

int anwGetNearbyNonEliteSupportCount(vector location = cInvalidVector, float radius = 26.0)
{
   if ((location == cInvalidVector) || (radius <= 0.0))
   {
      return (0);
   }

   int count = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, location, radius);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == true)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int anwGetTotalNonEliteTroopCount(void)
{
   int count = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == true)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int anwGetTotalEliteTroopCount(void)
{
   int count = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == false)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int anwGetNearbyEliteCoreCount(vector location = cInvalidVector, float radius = 30.0)
{
   if ((location == cInvalidVector) || (radius <= 0.0))
   {
      return (0);
   }

   int count = 0;

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive, location, radius);
   count = count + kbUnitQueryExecute(heroQueryID);

   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, location, radius);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == false)
      {
         continue;
      }

      count = count + 1;
   }

   return (count);
}

int anwGetThreatenedEliteAnchorID(void)
{
   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      if (anwGetNearbyEnemyPressureCount(kbUnitGetPosition(heroID), 28.0) > 0)
      {
         return (heroID);
      }
   }

   int eliteQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int eliteCount = kbUnitQueryExecute(eliteQueryID);
   i = 0;
   for (i = 0; < eliteCount)
   {
      int unitID = kbUnitQueryGetResult(eliteQueryID, i);
      if (anwIsEliteUnit(unitID) == false)
      {
         continue;
      }

      if (anwGetNearbyEnemyPressureCount(kbUnitGetPosition(unitID), 28.0) > 0)
      {
         return (unitID);
      }
   }

   return (-1);
}

int anwGetPrimaryLandAttackPlanID(void)
{
   int numPlans = aiPlanGetActiveCount();
   int i = 0;
   for (i = 0; < numPlans)
   {
      int planID = aiPlanGetIDByActiveIndex(i);
      if (aiPlanGetType(planID) != cPlanCombat)
      {
         continue;
      }

      if (aiPlanGetVariableInt(planID, cCombatPlanCombatType, 0) != cCombatPlanCombatTypeAttack)
      {
         continue;
      }

      if (aiPlanGetParentID(planID) >= 0)
      {
         continue;
      }

      if ((planID == gNavyAttackPlan) || (planID == gLandPatrolPlan) || (planID == gWaterPatrolPlan) ||
          (planID == gWaterDockAttackPlan) || (planID == gWarshipExplorePlan) || (planID == gIslandAssaultPlanID) ||
          (planID == gKOTHCombatPlan) || (planID == gKOTHGuardPlan) || (planID == gIslandSearchPlanID) ||
          (planID == gANWEliteSupportPlanID))
      {
         continue;
      }

      return (planID);
   }

   return (-1);
}

vector anwGetAttackPlanGatherPoint(int attackPlanID = -1)
{
   if (attackPlanID < 0)
   {
      return (cInvalidVector);
   }

   vector gatherPoint = aiPlanGetVariableVector(attackPlanID, cCombatPlanGatherPoint, 0);
   if (gatherPoint != cInvalidVector)
   {
      return (gatherPoint);
   }

   return (anwGetEliteRetreatPoint());
}

vector anwGetAttackPlanTargetPoint(int attackPlanID = -1)
{
   if (attackPlanID < 0)
   {
      return (cInvalidVector);
   }

   vector targetPoint = aiPlanGetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0);
   if (targetPoint != cInvalidVector)
   {
      return (targetPoint);
   }

   int targetPlayer = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetPlayerID, 0);
   int targetBaseID = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetBaseID, 0);
   if ((targetPlayer >= 0) && (targetBaseID >= 0))
   {
      targetPoint = kbBaseGetLocation(targetPlayer, targetBaseID);
   }

   return (targetPoint);
}

vector anwGetAttackPlanStrategicPoint(int attackPlanID = -1)
{
   if (attackPlanID < 0)
   {
      return (cInvalidVector);
   }

   int targetPlayer = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetPlayerID, 0);
   int targetBaseID = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetBaseID, 0);
   if ((targetPlayer >= 0) && (targetBaseID >= 0))
   {
      vector basePoint = kbBaseGetLocation(targetPlayer, targetBaseID);
      if (basePoint != cInvalidVector)
      {
         return (basePoint);
      }
   }

   return (anwGetAttackPlanTargetPoint(attackPlanID));
}

int anwGetPrimaryExplorerID(void)
{
   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   if (kbUnitQueryExecute(heroQueryID) <= 0)
   {
      return (-1);
   }

   return (kbUnitQueryGetResult(heroQueryID, 0));
}

vector anwGetEnemyArmyMassPoint(int targetPlayer = -1, vector nearPoint = cInvalidVector, float radius = 42.0)
{
   if (nearPoint == cInvalidVector)
   {
      return (cInvalidVector);
   }

   int playerRelation = targetPlayer >= 0 ? targetPlayer : cPlayerRelationEnemyNotGaia;
   int enemyQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, playerRelation, cUnitStateAlive, nearPoint, radius);
   int enemyCount = kbUnitQueryExecute(enemyQueryID);
   if (enemyCount <= 0)
   {
      return (cInvalidVector);
   }

   float xTotal = 0.0;
   float zTotal = 0.0;
   int i = 0;
   for (i = 0; < enemyCount)
   {
      vector unitPosition = kbUnitGetPosition(kbUnitQueryGetResult(enemyQueryID, i));
      xTotal = xTotal + xsVectorGetX(unitPosition);
      zTotal = zTotal + xsVectorGetZ(unitPosition);
   }

   return (xsVectorSet(xTotal / enemyCount, 0.0, zTotal / enemyCount));
}

int anwGetBestEnemyExplorerStrikeID(int targetPlayer = -1, vector referencePoint = cInvalidVector, float searchRadius = 70.0,
   int maxEscortCount = 4)
{
   int playerRelation = targetPlayer >= 0 ? targetPlayer : cPlayerRelationEnemyNotGaia;
   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, playerRelation, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int bestHeroID = -1;
   float bestScore = 99999.0;

   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      vector heroPosition = kbUnitGetPosition(heroID);
      if ((referencePoint != cInvalidVector) && (distance(referencePoint, heroPosition) > searchRadius))
      {
         continue;
      }

      int escortQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, kbUnitGetPlayerID(heroID), cUnitStateAlive,
         heroPosition, 18.0);
      int escortCount = kbUnitQueryExecute(escortQueryID);
      if (escortCount > maxEscortCount)
      {
         continue;
      }

      float score = escortCount * 8.0;
      if (referencePoint != cInvalidVector)
      {
         score = score + distance(referencePoint, heroPosition);
      }

      if (score < bestScore)
      {
         bestScore = score;
         bestHeroID = heroID;
      }
   }

   return (bestHeroID);
}

bool anwIsEnemyExplorerInBattle(int heroID = -1, vector enemyArmyPoint = cInvalidVector, float battleRadius = 24.0)
{
   if (heroID < 0)
   {
      return (false);
   }

   vector heroPosition = kbUnitGetPosition(heroID);
   if (enemyArmyPoint == cInvalidVector)
   {
      return (anwGetNearbyEnemyPressureCount(heroPosition, battleRadius) > 4);
   }

   if (distance(heroPosition, enemyArmyPoint) > battleRadius)
   {
      return (false);
   }

   return (anwGetNearbyEnemyPressureCount(heroPosition, battleRadius) > 4);
}

void anwDestroyEliteGuardPlan(void)
{
   if (gANWEliteGuardPlanID >= 0)
   {
      anwLogPlanEvent("destroy", gANWEliteGuardPlanID, "name=ANW Elite Guard");
      aiPlanDestroy(gANWEliteGuardPlanID);
   }

   gANWEliteGuardPlanID = -1;
   gANWEliteGuardAnchorUnitID = -1;
   anwProbe("event.elite.guard_destroyed", "atMs=" + xsGetTime());
}

void anwDestroyEliteSupportPlan(void)
{
   if (gANWEliteSupportPlanID >= 0)
   {
      anwLogPlanEvent("destroy", gANWEliteSupportPlanID, "name=ANW Elite Support");
      aiPlanDestroy(gANWEliteSupportPlanID);
   }

   gANWEliteSupportPlanID = -1;
   gANWEliteSupportAttackPlanID = -1;
   gANWEliteSupportLastRefreshTime = -1;
   anwProbe("event.elite.support_destroyed", "atMs=" + xsGetTime());
}

void anwDestroyExplorerEscortPlan(void)
{
   if (gANWExplorerEscortPlanID >= 0)
   {
      anwLogPlanEvent("destroy", gANWExplorerEscortPlanID, "name=ANW Explorer Escort");
      aiPlanDestroy(gANWExplorerEscortPlanID);
   }

   gANWExplorerEscortPlanID = -1;
   gANWExplorerEscortAttackPlanID = -1;
   gANWExplorerEscortLastRefreshTime = -1;
   anwProbe("event.elite.escort_destroyed", "atMs=" + xsGetTime());
}

void anwResetExplorerControlToBase(void)
{
   if (gExplorerControlPlan < 0)
   {
      return;
   }

   vector retreatPoint = anwGetEliteRetreatPoint();
   if (retreatPoint == cInvalidVector)
   {
      return;
   }

   aiPlanSetVariableVector(gExplorerControlPlan, cCombatPlanTargetPoint, 0, retreatPoint);
   anwProbe("event.elite.explorer_reset", "loc=" + anwFmtVec(retreatPoint));
}

void anwPositionExplorerBehindArmy(vector rearPoint = cInvalidVector)
{
   if (rearPoint == cInvalidVector)
   {
      return;
   }
   anwProbe("event.elite.explorer_rear", "loc=" + anwFmtVec(rearPoint));

   if (gExplorerControlPlan >= 0)
   {
      aiPlanSetVariableVector(gExplorerControlPlan, cCombatPlanTargetPoint, 0, rearPoint);
   }

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      int currentPlanID = kbUnitGetPlanID(heroID);
      if ((currentPlanID >= 0) && (currentPlanID != gExplorerControlPlan))
      {
         aiPlanRemoveUnit(currentPlanID, heroID);
      }
      anwLogUnitAction("explorer-reposition", heroID, "destination=" + rearPoint);
      aiTaskUnitMove(heroID, rearPoint);
   }
}

void anwRebuildExplorerEscortPlan(int attackPlanID = -1, vector gatherPoint = cInvalidVector, vector escortPoint = cInvalidVector,
   int desiredEscortCount = 0)
{
   if ((attackPlanID < 0) || (gatherPoint == cInvalidVector) || (escortPoint == cInvalidVector) || (desiredEscortCount <= 0))
   {
      anwDestroyExplorerEscortPlan();
      return;
   }

   anwDestroyExplorerEscortPlan();

   int mainBaseID = kbBaseGetMainID(cMyID);
   int planID = aiPlanCreate("ANW Explorer Escort", cPlanCombat);
   anwLogPlanEvent("create", planID, "name=ANW Explorer Escort attackPlan=" + attackPlanID);
   aiPlanSetVariableInt(planID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
   aiPlanSetVariableInt(planID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(planID, cCombatPlanTargetPoint, 0, escortPoint);
   aiPlanSetVariableVector(planID, cCombatPlanGatherPoint, 0, gatherPoint);
   aiPlanSetVariableFloat(planID, cCombatPlanTargetEngageRange, 0, 16.0);
   aiPlanSetVariableFloat(planID, cCombatPlanGatherDistance, 0, 8.0);
   aiPlanSetVariableInt(planID, cCombatPlanRefreshFrequency, 0, 200);
   aiPlanSetVariableInt(planID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetDesiredPriority(planID, 88);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetInitialPosition(planID, gatherPoint);

   int addedUnits = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == true)
      {
         continue;
      }

      int currentPlanID = kbUnitGetPlanID(unitID);
      if ((currentPlanID != attackPlanID) && (currentPlanID != gANWExplorerEscortPlanID))
      {
         continue;
      }

      vector unitLocation = kbUnitGetPosition(unitID);
      if ((distance(unitLocation, escortPoint) > 46.0) && (distance(unitLocation, gatherPoint) > 42.0))
      {
         continue;
      }

      if ((currentPlanID >= 0) && (currentPlanID != planID))
      {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }

      aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(unitID), 0, 0, 1);
      if (aiPlanAddUnit(planID, unitID) == true)
      {
         addedUnits = addedUnits + 1;
      }

      if (addedUnits >= desiredEscortCount)
      {
         break;
      }
   }

   if (addedUnits <= 0)
   {
      anwLogPlanEvent("destroy", planID, "reason=no escort units added");
      aiPlanDestroy(planID);
      return;
   }

   aiPlanSetActive(planID);
   gANWExplorerEscortPlanID = planID;
   gANWExplorerEscortAttackPlanID = attackPlanID;
   gANWExplorerEscortLastRefreshTime = xsGetTime();
   debugANW("created explorer escort plan " + planID + " for attack plan " + attackPlanID +
      " using " + addedUnits + " non-elite troops.");
   anwProbe("elite.escort", "plan=" + planID + " attackPlan=" + attackPlanID +
      " units=" + addedUnits + " desired=" + desiredEscortCount + " escortPt=" + anwFmtVec(escortPoint));
}

vector anwChooseAssaultObjectivePoint(int attackPlanID = -1, vector gatherPoint = cInvalidVector)
{
   vector strategicPoint = anwGetAttackPlanStrategicPoint(attackPlanID);
   if (strategicPoint == cInvalidVector)
   {
      return (cInvalidVector);
   }

   int targetPlayer = aiPlanGetVariableInt(attackPlanID, cCombatPlanTargetPlayerID, 0);
   float decapitationBias = anwGetDecapitationBias();
   float protectionBias = anwGetExplorerProtectionBias();
   vector bulkPoint = anwGetEnemyArmyMassPoint(targetPlayer, strategicPoint, 44.0);
   if (bulkPoint == cInvalidVector)
   {
      aiPlanSetVariableInt(attackPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
      aiPlanSetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0, strategicPoint);
      return (strategicPoint);
   }

   int enemyExplorerID = anwGetBestEnemyExplorerStrikeID(targetPlayer, strategicPoint, 72.0,
      2 + ((1.0 - decapitationBias) * 4.0));
   if ((enemyExplorerID >= 0) && (decapitationBias >= 0.55) &&
       (anwIsEnemyExplorerInBattle(enemyExplorerID, bulkPoint, 26.0) == true))
   {
      vector strikePoint = kbUnitGetPosition(enemyExplorerID);
      if ((distance(strikePoint, bulkPoint) <= 26.0) || (decapitationBias >= 0.80))
      {
         aiPlanSetVariableInt(attackPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
         aiPlanSetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0, strikePoint);
         debugANW("assault objective shifted toward enemy explorer at " + strikePoint +
            " because leader doctrine favors decapitation strikes.");
         anwSendLeaderDecapitationLine(targetPlayer, 150000);
         return (strikePoint);
      }
   }

   aiPlanSetVariableInt(attackPlanID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(attackPlanID, cCombatPlanTargetPoint, 0, bulkPoint);
   if (protectionBias >= 0.45)
   {
      debugANW("assault objective shifted onto the bulk enemy force to preserve leader escort integrity.");
   }
   anwSendLeaderBulkAssaultLine(targetPlayer, 150000);
   return (bulkPoint);
}

void anwRebuildEliteGuardPlan(int anchorUnitID = -1)
{
   if (anchorUnitID < 0)
   {
      anwDestroyEliteGuardPlan();
      return;
   }

   vector anchorLocation = kbUnitGetPosition(anchorUnitID);
   if (anchorLocation == cInvalidVector)
   {
      anwDestroyEliteGuardPlan();
      return;
   }

   anwDestroyEliteGuardPlan();

   int planID = aiPlanCreate("ANW Elite Guard", cPlanCombat);
   anwLogPlanEvent("create", planID, "name=ANW Elite Guard anchorUnit=" + anchorUnitID);
   aiPlanSetVariableInt(planID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
   aiPlanSetVariableInt(planID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(planID, cCombatPlanTargetPoint, 0, anchorLocation);
   aiPlanSetVariableFloat(planID, cCombatPlanTargetEngageRange, 0, 26.0);
   aiPlanSetVariableFloat(planID, cCombatPlanGatherDistance, 0, 14.0);
   aiPlanSetVariableInt(planID, cCombatPlanRefreshFrequency, 0, 200);
   aiPlanSetVariableInt(planID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetDesiredPriority(planID, 70);

   int addedUnits = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, anchorLocation, 34.0);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == true)
      {
         continue;
      }

      int currentPlanID = kbUnitGetPlanID(unitID);
      if (currentPlanID >= 0)
      {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }

      aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(unitID), 0, 0, 1);
      if (aiPlanAddUnit(planID, unitID) == true)
      {
         addedUnits = addedUnits + 1;
      }

      if (addedUnits >= 16)
      {
         break;
      }
   }

   if (addedUnits <= 0)
   {
      anwLogPlanEvent("destroy", planID, "reason=no guard units added");
      aiPlanDestroy(planID);
      return;
   }

   aiPlanSetActive(planID);
   gANWEliteGuardPlanID = planID;
   gANWEliteGuardAnchorUnitID = anchorUnitID;
   debugANW("created elite guard plan " + planID + " around anchor unit " + anchorUnitID +
      " using " + addedUnits + " non-elite troops.");
   anwProbe("elite.guard", "plan=" + planID + " anchor=" + anchorUnitID +
      " units=" + addedUnits + " pos=" + anwFmtVec(anchorLocation));
}

void anwRetreatEliteCore(int anchorUnitID = -1, float radius = 36.0)
{
   if (anchorUnitID < 0)
   {
      return;
   }

   vector anchorLocation = kbUnitGetPosition(anchorUnitID);
   if (anchorLocation == cInvalidVector)
   {
      return;
   }

   vector retreatPoint = anwGetEliteRetreatPoint();
   if (retreatPoint == cInvalidVector)
   {
      return;
   }

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive, anchorLocation, radius);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      int currentPlanID = kbUnitGetPlanID(heroID);
      if (currentPlanID >= 0)
      {
         aiPlanRemoveUnit(currentPlanID, heroID);
      }
      anwLogUnitAction("elite-retreat-hero", heroID, "destination=" + retreatPoint);
      aiTaskUnitMove(heroID, retreatPoint);
   }

   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive, anchorLocation, radius);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == false)
      {
         continue;
      }

      int unitPlanID = kbUnitGetPlanID(unitID);
      if (unitPlanID >= 0)
      {
         aiPlanRemoveUnit(unitPlanID, unitID);
      }
      anwLogUnitAction("elite-retreat-core", unitID, "destination=" + retreatPoint);
      aiTaskUnitMove(unitID, retreatPoint);
   }

   debugANW("elite core around anchor unit " + anchorUnitID + " ordered to retreat to " + retreatPoint + ".");
   anwProbe("event.elite.retreat_core",
      "anchor=" + anchorUnitID + " radius=" + radius +
      " heroes=" + heroCount + " elites=" + numberFound +
      " loc=" + anwFmtVec(retreatPoint));
}

void anwRetreatAllEliteUnits(void)
{
   vector retreatPoint = anwGetEliteRetreatPoint();
   if (retreatPoint == cInvalidVector)
   {
      return;
   }

   int heroQueryID = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive);
   int heroCount = kbUnitQueryExecute(heroQueryID);
   int i = 0;
   for (i = 0; < heroCount)
   {
      int heroID = kbUnitQueryGetResult(heroQueryID, i);
      int currentPlanID = kbUnitGetPlanID(heroID);
      if (currentPlanID >= 0)
      {
         aiPlanRemoveUnit(currentPlanID, heroID);
      }
      anwLogUnitAction("elite-global-retreat-hero", heroID, "destination=" + retreatPoint);
      aiTaskUnitMove(heroID, retreatPoint);
   }

   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == false)
      {
         continue;
      }

      int unitPlanID = kbUnitGetPlanID(unitID);
      if (unitPlanID >= 0)
      {
         aiPlanRemoveUnit(unitPlanID, unitID);
      }
      anwLogUnitAction("elite-global-retreat-core", unitID, "destination=" + retreatPoint);
      aiTaskUnitMove(unitID, retreatPoint);
   }

   anwResetExplorerControlToBase();
   debugANW("all elite units were ordered to retreat after the explorer fell.");
   anwSendLeaderRetreatLine(cPlayerRelationEnemyNotGaia, 180000);
   anwProbe("event.elite.retreat_all",
      "heroes=" + heroCount + " elites=" + numberFound +
      " loc=" + anwFmtVec(retreatPoint));
}

void anwTryRansomExplorer(void)
{
   if (aiGetFallenExplorerID() < 0)
   {
      return;
   }

   if (aiPlanGetIDByTypeAndVariableType(cPlanResearch, cResearchPlanProtoUnitCommandID, cProtoUnitCommandRansomExplorer) >= 0)
   {
      return;
   }

   int tcID = getUnit(cUnitTypeTownCenter, cMyID, cUnitStateAlive);
   if (tcID < 0)
   {
      return;
   }

   createProtoUnitCommandResearchPlan(cProtoUnitCommandRansomExplorer, tcID, cMilitaryEscrowID, 95, 95);
   debugANW("queued explorer ransom through the town center command after losing the leader.");
   anwProbe("elite.ransom", "tc=" + tcID + " fallen=" + aiGetFallenExplorerID());
}

void anwRebuildEliteSupportPlan(int attackPlanID = -1, vector gatherPoint = cInvalidVector, vector elitePoint = cInvalidVector,
   int desiredEliteCount = 1)
{
   if ((attackPlanID < 0) || (elitePoint == cInvalidVector) || (desiredEliteCount <= 0))
   {
      anwDestroyEliteSupportPlan();
      return;
   }

   anwDestroyEliteSupportPlan();

   int mainBaseID = kbBaseGetMainID(cMyID);
   int planID = aiPlanCreate("ANW Elite Support", cPlanCombat);
   anwLogPlanEvent("create", planID, "name=ANW Elite Support attackPlan=" + attackPlanID);
   aiPlanSetVariableInt(planID, cCombatPlanCombatType, 0, cCombatPlanCombatTypeDefend);
   aiPlanSetVariableInt(planID, cCombatPlanTargetMode, 0, cCombatPlanTargetModePoint);
   aiPlanSetVariableVector(planID, cCombatPlanTargetPoint, 0, elitePoint);
   aiPlanSetVariableVector(planID, cCombatPlanGatherPoint, 0, gatherPoint);
   aiPlanSetVariableFloat(planID, cCombatPlanTargetEngageRange, 0, 24.0);
   aiPlanSetVariableFloat(planID, cCombatPlanGatherDistance, 0, 12.0);
   aiPlanSetVariableInt(planID, cCombatPlanRefreshFrequency, 0, 200);
   aiPlanSetVariableInt(planID, cCombatPlanRetreatMode, 0, cCombatPlanRetreatModeNone);
   aiPlanSetDesiredPriority(planID, 82);
   aiPlanSetBaseID(planID, mainBaseID);
   aiPlanSetInitialPosition(planID, gatherPoint);

   int addedUnits = 0;
   int unitQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive);
   int numberFound = kbUnitQueryExecute(unitQueryID);
   int i = 0;
   for (i = 0; < numberFound)
   {
      int unitID = kbUnitQueryGetResult(unitQueryID, i);
      if (anwIsEliteUnit(unitID) == false)
      {
         continue;
      }

      vector unitLocation = kbUnitGetPosition(unitID);
      int currentPlanID = kbUnitGetPlanID(unitID);
      if ((currentPlanID != attackPlanID) && (currentPlanID != gANWEliteSupportPlanID) &&
          ((distance(unitLocation, elitePoint) > 60.0) && (distance(unitLocation, gatherPoint) > 55.0)))
      {
         continue;
      }

      if ((currentPlanID >= 0) && (currentPlanID != planID))
      {
         aiPlanRemoveUnit(currentPlanID, unitID);
      }

      aiPlanAddUnitType(planID, kbUnitGetProtoUnitID(unitID), 0, 0, 1);
      if (aiPlanAddUnit(planID, unitID) == true)
      {
         addedUnits = addedUnits + 1;
      }

      if (addedUnits >= desiredEliteCount)
      {
         break;
      }
   }

   if (addedUnits <= 0)
   {
      anwLogPlanEvent("destroy", planID, "reason=no elite support units added");
      aiPlanDestroy(planID);
      return;
   }

   aiPlanSetActive(planID);
   gANWEliteSupportPlanID = planID;
   gANWEliteSupportAttackPlanID = attackPlanID;
   gANWEliteSupportLastRefreshTime = xsGetTime();
   debugANW("created elite support plan " + planID + " for attack plan " + attackPlanID +
      " with " + addedUnits + " elite units guarding the second line.");
   anwProbe("elite.support", "plan=" + planID + " attackPlan=" + attackPlanID +
      " units=" + addedUnits + " desired=" + desiredEliteCount + " elitePt=" + anwFmtVec(elitePoint));
}

bool anwHandleEliteAssaultFormation(int attackPlanID = -1)
{
   static int lastProbedAssaultPlan = -1;
   if (attackPlanID < 0)
   {
      anwDestroyEliteSupportPlan();
      return (false);
   }

   vector gatherPoint = anwGetAttackPlanGatherPoint(attackPlanID);
   vector targetPoint = anwChooseAssaultObjectivePoint(attackPlanID, gatherPoint);
   if (attackPlanID != lastProbedAssaultPlan)
   {
      lastProbedAssaultPlan = attackPlanID;
      anwProbe("elite.assault", "attackPlan=" + attackPlanID +
         " gather=" + anwFmtVec(gatherPoint) + " target=" + anwFmtVec(targetPoint));
   }
   if ((gatherPoint == cInvalidVector) || (targetPoint == cInvalidVector))
   {
      anwDestroyExplorerEscortPlan();
      anwDestroyEliteSupportPlan();
      return (false);
   }

   int nonEliteCount = anwGetTotalNonEliteTroopCount();
   int eliteCount = anwGetTotalEliteTroopCount();
   int totalArmyCount = nonEliteCount + eliteCount;
   bool largeArmy = ((nonEliteCount >= 12) && (totalArmyCount >= 18));
   float protectionBias = anwGetExplorerProtectionBias();
   float decapitationBias = anwGetDecapitationBias();

   float eliteOffset = 7.0;
   float explorerOffset = 14.0 + (protectionBias * 10.0) - (decapitationBias * 4.0) + gANWExplorerRearOffsetBonus;
   int desiredEliteCount = 1;
   int desiredEscortCount = 2 + (protectionBias * 5.0) + gANWExplorerEscortBonus;
   if (largeArmy == true)
   {
      eliteOffset = 13.0;
      explorerOffset = explorerOffset + 6.0;
      desiredEliteCount = eliteCount;
      desiredEscortCount = desiredEscortCount + 2;
      if (desiredEliteCount > 6)
      {
         desiredEliteCount = 6;
      }
   }
   else if (eliteCount > 1)
   {
      desiredEliteCount = 2;
   }

   if (decapitationBias >= 0.70)
   {
      desiredEscortCount = desiredEscortCount - 1;
   }

   if (desiredEscortCount < 2)
   {
      desiredEscortCount = 2;
   }

   int escortCap = nonEliteCount / 3;
   if (escortCap < 2)
   {
      escortCap = 2;
   }
   if (desiredEscortCount > escortCap)
   {
      desiredEscortCount = escortCap;
   }

   vector elitePoint = anwGetAssaultOffsetPoint(gatherPoint, targetPoint, eliteOffset);
   vector explorerPoint = anwGetAssaultOffsetPoint(gatherPoint, targetPoint, explorerOffset);

   anwPositionExplorerBehindArmy(explorerPoint);

   if ((nonEliteCount <= 0) || (eliteCount <= 0))
   {
      anwDestroyExplorerEscortPlan();
      anwDestroyEliteSupportPlan();
      return (true);
   }

    if ((gANWExplorerEscortPlanID < 0) || (gANWExplorerEscortAttackPlanID != attackPlanID) ||
        (xsGetTime() - gANWExplorerEscortLastRefreshTime >= 12000))
    {
       anwRebuildExplorerEscortPlan(attackPlanID, gatherPoint, explorerPoint, desiredEscortCount);
    }
    else
    {
       aiPlanSetVariableVector(gANWExplorerEscortPlanID, cCombatPlanTargetPoint, 0, explorerPoint);
       aiPlanSetVariableVector(gANWExplorerEscortPlanID, cCombatPlanGatherPoint, 0, gatherPoint);
    }

   if ((gANWEliteSupportPlanID < 0) || (gANWEliteSupportAttackPlanID != attackPlanID) ||
       (xsGetTime() - gANWEliteSupportLastRefreshTime >= 15000))
   {
      anwRebuildEliteSupportPlan(attackPlanID, gatherPoint, elitePoint, desiredEliteCount);
   }
   else
   {
      aiPlanSetVariableVector(gANWEliteSupportPlanID, cCombatPlanTargetPoint, 0, elitePoint);
      aiPlanSetVariableVector(gANWEliteSupportPlanID, cCombatPlanGatherPoint, 0, gatherPoint);
   }

   return (true);
}

rule anwEliteGuardMonitor
inactive
minInterval 5
{
   static int probedFirstTick = 0;
   static int probedFallenOnce = 0;
   if (probedFirstTick == 0)
   {
      // LL-GUARD probe — fires once per AI on first monitor tick, confirms
      // the elite-guard/explorer-escort rule is actually running.
      anwProbe("elite.guardTick", "note=monitor-first-tick");
      probedFirstTick = 1;
   }
   anwLogRuleTick("anwEliteGuardMonitor");
   if (aiGetFallenExplorerID() >= 0)
   {
      if (probedFallenOnce == 0)
      {
         // LL-EXPLOST probe — records the moment the AI's explorer died
         // (maps to ToAllyILoseExplorerEnemy quote trigger). One-shot.
         anwProbe("elite.explorerLost", "explorer=" + aiGetFallenExplorerID());
         probedFallenOnce = 1;
      }
      anwDestroyEliteGuardPlan();
      anwDestroyExplorerEscortPlan();
      anwDestroyEliteSupportPlan();
      anwRetreatAllEliteUnits();
      anwTryRansomExplorer();
      return;
   }

   int attackPlanID = anwGetPrimaryLandAttackPlanID();
   if (attackPlanID >= 0)
   {
      // mil.escort_check — emitted every monitor tick while an attack plan
      // is active. Records how far the leader/explorer unit is from the
      // nearest friendly land-military unit so the offline validator can
      // assert the leader stays within 30 m of the army during attacks.
      int explorerID = anwGetPrimaryExplorerID();
      vector explorerPos = cInvalidVector;
      float nearestDist = -1.0;
      if (explorerID >= 0)
      {
         explorerPos = kbUnitGetPosition(explorerID);
      }
      if (explorerPos != cInvalidVector)
      {
         int milQueryID = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary, cMyID, cUnitStateAlive,
            explorerPos, 60.0);
         int milCount = kbUnitQueryExecute(milQueryID);
         for (mi = 0; < milCount)
         {
            int milUnit = kbUnitQueryGetResult(milQueryID, mi);
            float d = distance(explorerPos, kbUnitGetPosition(milUnit));
            if ((nearestDist < 0.0) || (d < nearestDist))
            {
               nearestDist = d;
            }
         }
      }
      anwProbe("mil.escort_check",
         "attack_active=1" +
         " leader_dist=" + nearestDist +
         " explorerID=" + explorerID +
         " attackPlan=" + attackPlanID);
      anwDestroyEliteGuardPlan();
      if (anwHandleEliteAssaultFormation(attackPlanID) == true)
      {
         return;
      }
   }
   else
   {
      anwDestroyExplorerEscortPlan();
      anwDestroyEliteSupportPlan();
      anwResetExplorerControlToBase();
   }

   int anchorUnitID = anwGetThreatenedEliteAnchorID();
   if (anchorUnitID < 0)
   {
      anwDestroyEliteGuardPlan();
      return;
   }

   vector anchorLocation = kbUnitGetPosition(anchorUnitID);
   int enemyPressure = anwGetNearbyEnemyPressureCount(anchorLocation, 28.0);
   if (enemyPressure <= 0)
   {
      anwDestroyEliteGuardPlan();
      return;
   }

   int nearbyScreenCount = anwGetNearbyNonEliteSupportCount(anchorLocation, 26.0);
   if (nearbyScreenCount > 0)
   {
      if ((gANWEliteGuardPlanID < 0) || (gANWEliteGuardAnchorUnitID != anchorUnitID))
      {
         anwRebuildEliteGuardPlan(anchorUnitID);
      }
      else
      {
         aiPlanSetVariableVector(gANWEliteGuardPlanID, cCombatPlanTargetPoint, 0, anchorLocation);
      }
      return;
   }

   anwDestroyEliteGuardPlan();

   if (anwGetTotalNonEliteTroopCount() > 0)
   {
      return;
   }

   int playstyleBucket = anwGetPlaystyleBucket();
   if (playstyleBucket >= 2)
   {
      debugANW("elite core remains engaged because leader playstyle is aggressive.");
      return;
   }

   if ((playstyleBucket == 1) && (enemyPressure <= anwGetNearbyEliteCoreCount(anchorLocation, 30.0)))
   {
      debugANW("elite core remains engaged because balanced leader still has a favorable local fight.");
      return;
   }

   anwRetreatEliteCore(anchorUnitID);
}

//==============================================================================
/* AI non-elite rout system (A New World).
 *
 * Behaviour spec (matches tools/validation/runtime_specs/anw_runtime_suites.json):
 *
 *   - Non-elite AI-controlled land military breaks when its hitpoints fall
 *     under 25% AND no elite/hero support is within 18 m. Broken units
 *     issue a retreat-to-main-base move command.
 *   - Elite units and any unit currently controlled by the human player
 *     keep their orders untouched.
 *   - Rout is blocked when an elite anchor is close — the screen body
 *     stays in formation around the elite line; this is the entire point
 *     of the elite-screen formation built earlier in this file.
 *
 * Debug markers (the validator looks for these strings verbatim):
 *
 *   "A New World: [RULE] AI non-elite rout enabled at 25% health; "
 *   "elite units hold and human-controlled units keep manual control"
 *       — one-shot, first tick of the rule, confirms boot.
 *
 *   "A New World: [UNIT] ai-rout-start unit=<ID>"   — first rout tick
 *   "A New World: [UNIT] ai-rout-move unit=<ID>"    — each subsequent tick still moving
 *   "A New World: [UNIT] ai-rout-arrival unit=<ID>" — within 6 m of destination
 *   "A New World: [UNIT] ai-rout-blocked unit=<ID> reason=elite-support"
 *       — emitted when a unit would have routed but an elite anchor was
 *         within range. Confirms the screen-body-stays-in-formation rule.
 *
 * Tracking: a single static xsArray of 32 tracked unit IDs plus a parallel
 * vector array for the per-unit destination. 32 is plenty — a typical AI
 * army has under 20 active engaged units and rout state only persists for
 * a few ticks per unit. Slots are reused round-robin; a dead/healed unit
 * frees its slot.
 */
//==============================================================================

extern int gANWAiRoutSlotsArrayID = -1;        // xsArrayCreateInt slots → unitID (-1 = free)
extern int gANWAiRoutDestArrayID = -1;         // xsArrayCreateVector slots → destination
extern int gANWAiRoutStartTimeArrayID = -1;    // xsArrayCreateInt slots → start time (s)
extern int gANWAiRoutSlotCount = 32;
extern int gANWAiRoutBootMarkerEmitted = 0;
extern int gANWAiRoutLastDestinationStaleCheck = -1;

// (gANWEliteProtoIDsArrayID / gANWEliteProtoCount / cANWEliteProtoMax are declared
//  at the top of this file so they precede their first use — see line ~24.)

const float cANWAiRoutHpThreshold       = 0.25;   // 25% health — non-unique units
const float cANWAiRoutEliteHpThreshold  = 0.10;   // 10% health — unique/nation-specific units
const float cANWAiRoutEliteSupportRange = 18.0;   // metres
const float cANWAiRoutArrivalTolerance  = 6.0;    // metres — "arrived" radius
const int   cANWAiRoutMaxLifetimeSecs   = 60;     // give up tracking after this

void anwEnsureAiRoutArrays(void)
{
   if (gANWAiRoutSlotsArrayID < 0)
   {
      gANWAiRoutSlotsArrayID = xsArrayCreateInt(gANWAiRoutSlotCount, -1, "LL ai-rout slots");
      gANWAiRoutStartTimeArrayID = xsArrayCreateInt(gANWAiRoutSlotCount, -1, "LL ai-rout start time");
      gANWAiRoutDestArrayID = xsArrayCreateVector(gANWAiRoutSlotCount, cInvalidVector, "LL ai-rout dest");
   }
}

int anwFindAiRoutSlotForUnit(int unitID = -1)
{
   if ((unitID < 0) || (gANWAiRoutSlotsArrayID < 0))
   {
      return (-1);
   }
   for (slot = 0; < gANWAiRoutSlotCount)
   {
      if (xsArrayGetInt(gANWAiRoutSlotsArrayID, slot) == unitID)
      {
         return (slot);
      }
   }
   return (-1);
}

int anwClaimAiRoutSlot(int unitID = -1, vector dest = cInvalidVector)
{
   if (unitID < 0)
   {
      return (-1);
   }
   anwEnsureAiRoutArrays();
   int existing = anwFindAiRoutSlotForUnit(unitID);
   if (existing >= 0)
   {
      return (existing);
   }
   for (slot = 0; < gANWAiRoutSlotCount)
   {
      if (xsArrayGetInt(gANWAiRoutSlotsArrayID, slot) < 0)
      {
         xsArraySetInt(gANWAiRoutSlotsArrayID, slot, unitID);
         xsArraySetInt(gANWAiRoutStartTimeArrayID, slot, xsGetTime());
         xsArraySetVector(gANWAiRoutDestArrayID, slot, dest);
         return (slot);
      }
   }
   return (-1);
}

void anwReleaseAiRoutSlot(int slot = -1)
{
   if ((slot < 0) || (gANWAiRoutSlotsArrayID < 0))
   {
      return;
   }
   xsArraySetInt(gANWAiRoutSlotsArrayID, slot, -1);
   xsArraySetInt(gANWAiRoutStartTimeArrayID, slot, -1);
   xsArraySetVector(gANWAiRoutDestArrayID, slot, cInvalidVector);
}

vector anwChooseAiRoutDestination(void)
{
   int mainBaseID = kbBaseGetMainID(cMyID);
   if (mainBaseID < 0)
   {
      return (cInvalidVector);
   }
   return (kbBaseGetLocation(cMyID, mainBaseID));
}

bool anwAiRoutHasEliteSupportNearby(vector pos = cInvalidVector)
{
   if (pos == cInvalidVector)
   {
      return (false);
   }
   // Heroes are explicitly counted as elite support per the elite-tactics
   // formation contract (line 26 of this file). anwIsEliteUnit() currently
   // returns false unconditionally — heroes carry the elite anchor role.
   int heroQuery = createSimpleUnitQuery(cUnitTypeHero, cMyID, cUnitStateAlive,
      pos, cANWAiRoutEliteSupportRange);
   int heroCount = kbUnitQueryExecute(heroQuery);
   if (heroCount > 0)
   {
      return (true);
   }
   return (false);
}

bool anwIsAiRoutEligibleUnit(int unitID = -1)
{
   if (unitID < 0)
   {
      return (false);
   }
   if (kbUnitGetPlayerID(unitID) != cMyID)
   {
      return (false);
   }
   // Heroes are elite anchors; never rout them via this system.
   if (kbUnitIsType(unitID, cUnitTypeHero) == true)
   {
      return (false);
   }
   // The explorer (subset of hero) gets its own escort/ransom logic
   // elsewhere in this file. Skip.
   if (kbUnitIsType(unitID, cUnitTypeExplorer) == true)
   {
      return (false);
   }
   // Mercenaries NEVER rout — for any faction (user directive). They are
   // bought, gold-only shock troops with no home-city morale to break; the
   // design intent is that they fight to the death rather than retreat. This
   // exemption precedes the elite/threshold branches below so a mercenary is
   // excluded regardless of its HP or any elite flag.
   if (kbUnitIsType(unitID, cUnitTypeMercenary) == true)
   {
      return (false);
   }
   // Out-of-scope: human-controlled units retain manual orders. The XS
   // engine only ticks rules for the *current* AI player, so any unit
   // owned by a human player is naturally filtered by the cMyID check
   // above. The contract is documented in the boot marker for clarity.
   // Unique (nation-specific) units retreat at 10%; all others at 25%.
   if (anwIsEliteUnit(unitID) == true)
   {
      return (kbUnitGetHealth(unitID) < cANWAiRoutEliteHpThreshold);
   }
   return (kbUnitGetHealth(unitID) < cANWAiRoutHpThreshold);
}

void anwProcessAiRoutTick(void)
{
   anwEnsureAiRoutArrays();

   // ── Pass 1: reap stale slots (dead units, healed units, expired) ──
   int now = xsGetTime();
   for (slot = 0; < gANWAiRoutSlotCount)
   {
      int trackedID = xsArrayGetInt(gANWAiRoutSlotsArrayID, slot);
      if (trackedID < 0)
      {
         continue;
      }
      // Dead or unknown → release.
      if (kbUnitGetCurrentHitpoints(trackedID) <= 0)
      {
         anwReleaseAiRoutSlot(slot);
         continue;
      }
      // Healed back above threshold → release (the unit is fine again).
      // NEW — release unique units when healed above 20%; non-unique above 35%
      float releaseThreshold = cANWAiRoutHpThreshold + 0.10;
      if (anwIsEliteUnit(trackedID) == true)
      {
         releaseThreshold = cANWAiRoutEliteHpThreshold + 0.10;
      }
      if (kbUnitGetHealth(trackedID) >= releaseThreshold)
      {
         anwReleaseAiRoutSlot(slot);
         continue;
      }
      // Expired → release (something else has happened, stop tracking).
      int startTime = xsArrayGetInt(gANWAiRoutStartTimeArrayID, slot);
      if ((startTime > 0) && ((now - startTime) > cANWAiRoutMaxLifetimeSecs))
      {
         anwReleaseAiRoutSlot(slot);
         continue;
      }
      // Arrived → emit and release.
      vector dest = xsArrayGetVector(gANWAiRoutDestArrayID, slot);
      vector pos = kbUnitGetPosition(trackedID);
      if (dest != cInvalidVector)
      {
         float distLeft = distance(pos, dest);
         if (distLeft <= cANWAiRoutArrivalTolerance)
         {
            debugANW("[UNIT] ai-rout-arrival unit=" + trackedID);
            anwProbe("rout.arrival", "unit=" + trackedID +
               " dist=" + distLeft + " elapsed=" + (now - startTime));
            anwReleaseAiRoutSlot(slot);
            continue;
         }
         // Still moving — emit the tick marker.
         debugANW("[UNIT] ai-rout-move unit=" + trackedID);
      }
   }

   // ── Pass 2: scan land military for new rout candidates ──
   vector routDest = anwChooseAiRoutDestination();
   if (routDest == cInvalidVector)
   {
      // No main base yet — nothing to rout toward. Bail.
      return;
   }
   int milQuery = createSimpleUnitQuery(cUnitTypeLogicalTypeLandMilitary,
      cMyID, cUnitStateAlive);
   int milCount = kbUnitQueryExecute(milQuery);
   for (i = 0; < milCount)
   {
      int unitID = kbUnitQueryGetResult(milQuery, i);
      if (anwIsAiRoutEligibleUnit(unitID) == false)
      {
         continue;
      }
      vector unitPos = kbUnitGetPosition(unitID);
      // Elite-support gating — broken unit holds line if an elite anchor
      // is in range. Per spec, emit the blocked marker once per visit so
      // the validator can observe the support-screen contract.
      if (anwAiRoutHasEliteSupportNearby(unitPos) == true)
      {
         // Only emit-blocked once per tracked unit per tick (we don't have
         // per-unit tick history, so emit once per tick at low rate).
         debugANW("[UNIT] ai-rout-blocked unit=" + unitID +
            " reason=elite-support");
         anwProbe("rout.blocked", "unit=" + unitID + " reason=elite-support");
         // If this unit had been routing, cancel — elite arrived to support.
         int oldSlot = anwFindAiRoutSlotForUnit(unitID);
         if (oldSlot >= 0)
         {
            anwReleaseAiRoutSlot(oldSlot);
         }
         continue;
      }
      int existingSlot = anwFindAiRoutSlotForUnit(unitID);
      if (existingSlot < 0)
      {
         int newSlot = anwClaimAiRoutSlot(unitID, routDest);
         if (newSlot >= 0)
         {
            aiTaskUnitMove(unitID, routDest);
            debugANW("[UNIT] ai-rout-start unit=" + unitID);
            anwProbe("rout.start", "unit=" + unitID +
               " hp=" + kbUnitGetHealth(unitID) +
               " isElite=" + anwIsEliteUnit(unitID) +
               " dest=" + anwFmtVec(routDest));
         }
      }
      else
      {
         // Already tracked — re-issue the move order in case the unit's
         // engagement was interrupted and it stopped moving. AoE3's
         // aiTaskUnitMove is idempotent against an active move order, so
         // this is cheap.
         aiTaskUnitMove(unitID, routDest);
      }
   }
}

//==============================================================================
// anwAiRoutMonitor — periodic monitor for the non-elite-rout system.
//
// Activated alongside anwEliteGuardMonitor in aiCore.xs (early-game
// hook in age2Monitor). Fires every 4 s — slightly more often than the
// elite guard's 5 s tick so a broken unit gets its retreat order within a
// single second of falling under threshold.
//
// The first tick emits the boot marker the runtime-logs validator looks
// for. Subsequent ticks emit per-unit start/move/arrival/blocked markers
// driven by anwProcessAiRoutTick().
//==============================================================================
rule anwAiRoutMonitor
inactive
minInterval 4
{
   if (gANWAiRoutBootMarkerEmitted == 0)
   {
      // Single literal (no concatenation) so the offline static-emitter
      // checker in tools/validation/validate_runtime_logs.py can see this
      // marker as a contiguous substring in the XS source.
      debugANW("[RULE] AI rout enabled: non-unique units at 25% HP, unique/nation-specific units at 10% HP; hero within 18m suppresses rout");
      // Resolve civ-unique elite unit type IDs once, now that kb is ready.
      anwInitEliteProtoIDs();
      anwProbe("rout.boot",
         "hp_threshold=" + cANWAiRoutHpThreshold +
         " elite_hp_threshold=" + cANWAiRoutEliteHpThreshold +
         " elite_support_range=" + cANWAiRoutEliteSupportRange +
         " arrival_tolerance=" + cANWAiRoutArrivalTolerance +
         " elite_protos=" + gANWEliteProtoCount);
      gANWAiRoutBootMarkerEmitted = 1;
   }
   anwLogRuleTick("anwAiRoutMonitor");
   anwProcessAiRoutTick();
}