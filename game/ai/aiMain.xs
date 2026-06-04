// Includes.
include "core/aiCore.xs";

//==============================================================================
/* main
   This function is called during the loading screen before the game has started.
   Some stuff isn't initialised yet at this point so we must account for this.
*/
//==============================================================================
void main(void)
{
   anwVerboseEcho("Main is starting");

   // Set our random seed, "-1" is a random init. 
   // Very important that this is done early so we can use our rand functions.
   aiRandSetSeed(-1);
   
   // Analyze the map, create area matrix. We call this here and not in analyseMap because 
   // it's very important this is done early and the arrays might need it.
   kbAreaCalculate();
   
   // Initialise all global civilisation specific unit types. (g****Unit variables)
   initCivUnitTypes();
   
   // Create the global arrays.
   initArrays();

   // Set up all variables related to game settings and type.
   analyzeGameSettingsAndType();
   
   // Set up all variables related to the map layout, excluding our starting units.
   analyzeMap();

   // Set up all XS handlers.
   initXSHandlers();
   
   // Find out what our personality is, we set our "btVariables" here, like btRushBoom.
   initPersonality();
   
   // Analyse our history with the players in the game and sent them an appropriate message.
   // AI aren't allowed to taunt in SPC and all the checks this func does fail during SPC anyway.
   if (gSPC == false)
   {
      startUpChats();
   }
   
   // Call the Enhanced AI function for some special magic.
   enhancedInit();

   // At this point in the chain we've set all cv/bt variables to what we think is right.
   // Now we can allow the loader file to change these values based on custom needs.
   // These variables (found in aiHeader.xs) will not be overriden again after this point.
   preInit();
   
   // Our bt/cv variables have been set to their final values.
   // See if we must adjust anything we did before this point to account for this.
   preInitFinal();

   // Everything we've done above is basically setting a whole bunch of variables based on stuff.
   // We haven't moved a single unit yet or made a single plan.
   // Below we're going to figure out what kind of start we're dealing with and actually do something.
   prepareForInit();

   // From here the chain goes like this:
   // SCENARIO: waitForStartup will keep querying for an AI Start object.
   // When it finds one it will decide if we're dealing with a TC, Covered Wagon, No TC start.
   // Then it will call init() -> shared part.
   // RANDOM MAP: we figure out if we're dealing with a TC or Covered Wagon (Nomad) start.
   // Then we will call init() -> shared part.
   // SHARED PART:
   // Init() will create a TC build plan if we have a Covered Wagon start.
   // It will call initEcon() and initMil() to get those areas set up and it will
   // enable a bunch of Rules that don't require a TC to be alive and call postInit() from the loader file.
   // It will also enable the townCenterComplete Rule.
   // Inside of townCenterComplete we keep querying to see if we have a TC, we need this to actually make sense of it all.
   // If we find a TC we enable the bulk of the rules and actually start playing for real.
   
}