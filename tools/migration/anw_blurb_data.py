"""Per-civ leader + nation history for the SELECT CIVILIZATION tooltip.

Each entry has only TWO authored fields:
  - leader_history:    1-2 sentences on the leader.
  - nation_history:    1-2 sentences on the state's historical context.

The unit/building information already in the existing tooltip strings
(which we believe to be authoritatively authored) is **preserved** by
``generate_civ_blurbs.py`` — it only PREPENDS the new leader+nation
sections. We don't claim to know every civ's unit roster off-hand.

Used by tools/migration/generate_civ_blurbs.py.
"""

BLURBS = {
    # ---- Renamed civs (base tokens) ------------------------------------
    "British": dict(
        leader_history="Reigned 1558-1603 as Queen of England and Ireland. Defeated the Spanish Armada in 1588 and presided over an Elizabethan Golden Age of exploration, theatre, and Atlantic privateering.",
        nation_history="The British Empire grew on Royal Navy supremacy, the East India Company, and global mercantile colonies. Wool, sugar and tea built the world's largest 19th-century imperium.",
    ),
    "French": dict(
        leader_history="Louis XVIII (r. 1814-1815, 1815-1824) reclaimed the Bourbon throne after Napoleon's fall, balancing Restoration legitimism with grudging concessions to revolutionary reforms.",
        nation_history="Bourbon France revolved around the Sun King's grand court, the dragoon and gendarmerie tradition, and the Catholic Ancien Régime that the Revolution would later overthrow.",
    ),
    "Spanish": dict(
        leader_history="Isabella I of Castile (r. 1474-1504) co-ruled with Ferdinand of Aragon, expelled the Moors at Granada, and personally chartered Columbus's 1492 voyage.",
        nation_history="The Spanish Empire of the Habsburgs and early Bourbons drew silver from Potosí and Mexico, fielded the Tercio infantry square, and converted the New World by sword and missionary.",
    ),
    "Portuguese": dict(
        leader_history="Prince Henry the Navigator (1394-1460) sponsored the great Atlantic-coast expeditions out of Sagres, opening the route around Africa toward the Indian Ocean spice trade.",
        nation_history="Portugal pioneered Europe's age of discovery — Brazil, Goa, Macau, and the African slave-trade triangle all flowed through Lisbon's caravel-and-carrack fleets.",
    ),
    "Dutch": dict(
        leader_history="Maurice of Nassau (r. 1585-1625) modernised European warfare with drilled musket lines, modular fortification, and the precise pay-and-supply that made his army a match for Spain.",
        nation_history="The Dutch Republic ran the 17th-century world economy through the Bank of Amsterdam and the East-India Company (VOC), trading from New Amsterdam to Batavia.",
    ),
    "Germans": dict(
        leader_history="Frederick the Great of Prussia (r. 1740-1786) drilled the Prussian army into Europe's most precise instrument and won Silesia from Habsburg Austria with oblique-order tactics.",
        nation_history="The German Empire (1871-1918) unified the German-speaking states under Hohenzollern Prussia, fielding the precision Prussian army, conscript Reichsheer, and the industrial Krupp arsenal.",
    ),
    "Russians": dict(
        leader_history="Ivan IV the Terrible (r. 1547-1584) crowned himself first Tsar of All Rus', conquered Kazan and Astrakhan, and unleashed the Oprichnik terror to break the boyars.",
        nation_history="Tsarist Russia welded together the Streltsy musketeer corps, vast peasant levies, and Orthodox missionary expansion across the Eurasian frontier.",
    ),
    "Ottomans": dict(
        leader_history="Mehmed II the Conqueror (r. 1444-1446, 1451-1481) breached Constantinople in 1453 with massive bombards, ending Byzantium and centralising the Ottoman state.",
        nation_history="The Sublime Porte maintained the Janissary slave-soldier corps, sipahi cavalry timars, and the millet system that ruled Sunni and non-Muslim subjects from Algiers to Baghdad.",
    ),
    "Chinese": dict(
        leader_history="The Kangxi Emperor (r. 1661-1722) of the Qing Dynasty consolidated Manchu rule over China, defeated the Three Feudatories, and patronised the great Qing-era encyclopedias and atlases.",
        nation_history="Qing Dynasty China commanded the world's largest population and economy, with the Eight Banners army, Confucian bureaucracy, and Forbidden City court at its centre.",
    ),
    "Japanese": dict(
        leader_history="Tokugawa Ieyasu (r. 1603-1605 as shogun) ended the Sengoku wars at Sekigahara in 1600 and founded the Tokugawa shogunate, which closed Japan to most foreigners for 250 years.",
        nation_history="Edo-period Japan was Sakoku — peace under the Tokugawa shogunate, samurai-bureaucrat governance, and the rising chonin merchant culture of Edo and Osaka.",
    ),
    "Indians": dict(
        leader_history="Akbar the Great (r. 1556-1605) — referenced here as the Maratha-era state — though the doctrine plays as Shivaji's hill-fort guerrilla model: the Marathas raided Mughal supply with light cavalry until they ruled most of the subcontinent.",
        nation_history="The Maratha Confederacy (1674-1818) eclipsed the Mughals through ganimi kava raiding, hill-fort networks, and a confederate Peshwa state stretching from Pune to the Himalayas.",
    ),
    "XPAztec": dict(
        leader_history="Motecuhzoma II Xocoyotzin (r. 1502-1520) presided over the Aztec Triple Alliance at its territorial zenith and was killed during the Spanish entrada of Cortés.",
        nation_history="The Aztec Triple Alliance bound Tenochtitlan, Texcoco and Tlacopan in tribute confederation; Xochiyaoyotl 'flower wars' fed the captive economy of Templo Mayor.",
    ),
    "DEInca": dict(
        leader_history="Túpac Inca Yupanqui (r. 1471-1493) — and the broader Sapa Inca line — pushed Tawantinsuyu to its fullest extent across the Andes from Quito to Santiago.",
        nation_history="The Inca Empire integrated four suyus along the qhapaq-ñan road network, terraced agriculture, mit'a labor tax, and quipu accounting — without a written language or wheel.",
    ),
    "XPIroquois": dict(
        leader_history="Hiawatha, with the Peacemaker Deganawida, founded the Haudenosaunee Confederacy (the Five Nations) in pre-contact times, binding the Iroquois nations under the Great Law of Peace.",
        nation_history="The Haudenosaunee Confederacy of Mohawk, Oneida, Onondaga, Cayuga and Seneca governed by clan-mother council, dominated the Eastern Woodlands fur trade, and played England and France against each other.",
    ),
    "XPSioux": dict(
        leader_history="Sitting Bull (Tȟatȟáŋka Íyotake), with Crazy Horse, led the Lakota and allied tribes to victory over Custer's 7th Cavalry at Little Bighorn in 1876.",
        nation_history="The Lakota Sioux were Plains horse warriors and bison hunters whose seven councils dominated the Northern Plains until the buffalo collapse and Wounded Knee.",
    ),
    "DEAmericans": dict(
        leader_history="George Washington (1732-1799) commanded the Continental Army to victory over Britain in 1781 and became first President of the United States in 1789.",
        nation_history="The early United States expanded westward via the Northwest Ordinance, the Louisiana Purchase, and Manifest Destiny — a republic of yeoman farmers, militia, and Atlantic merchants.",
    ),
    "DEMexicans": dict(
        leader_history="Miguel Hidalgo y Costilla (1753-1811) raised the Grito de Dolores in 1810 against Spain, igniting the Mexican War of Independence — though executed before its 1821 victory.",
        nation_history="The First Mexican Empire rose from Hidalgo and Iturbide's revolt, oscillating between centralist conservative and liberal-federal regimes through Texas, the Mexican-American War, and Maximilian.",
    ),
    "DEItalians": dict(
        leader_history="Giuseppe Garibaldi (1807-1882) led the Mille Redshirts through Sicily and Naples in 1860, decisively unifying southern Italy under Vittorio Emanuele II.",
        nation_history="The Kingdom of Italy (1861-1946) wove Risorgimento republicans, Sardinian monarchists and the Pope's reluctant Romans into a single Latin nation-state.",
    ),
    "DEMaltese": dict(
        leader_history="Jean Parisot de Valette (1494-1568), Grand Master of the Knights Hospitaller, led the heroic defence of Malta in the 1565 Great Siege against Ottoman besiegers.",
        nation_history="The Order of Saint John ruled Malta (1530-1798) as a corsair-and-fortress state — Hospitaller crusaders bound by triple vows, funded by piracy on Ottoman shipping.",
    ),
    "DESwedish": dict(
        leader_history="Gustavus Adolphus (r. 1611-1632), the Lion of the North, revolutionised European warfare with combined arms — light cannon, salvo musket fire and Hakkapelit cavalry — until his death at Lützen.",
        nation_history="The Swedish Empire (1611-1721) rose to dominate the Baltic on the Carolean line-infantry doctrine before falling to Peter the Great's Russia at Poltava.",
    ),
    "DEHausa": dict(
        leader_history="Usman dan Fodio (1754-1817) led the 1804 Fulani jihad that overthrew the Hausa city-state kings and founded the Sokoto Caliphate centred on his son Muhammad Bello.",
        nation_history="The Sokoto Caliphate (1804-1903) bound the Hausaland city-states under Sharia governance, slave-cavalry warfare, and trans-Saharan caravan trade until the British conquest.",
    ),
    "DEEthiopians": dict(
        leader_history="Menelik II (r. 1889-1913) crushed the Italian invasion at Adwa in 1896, securing Ethiopian independence and modernising the empire from Addis Ababa.",
        nation_history="The Ethiopian Empire repelled European colonisation alone in Africa, fielding Solomonic monarchy, Coptic Christianity, and the highland fortress system.",
    ),

    # ---- Civs that kept ANW prefix (no base counterpart) ---------------
    "ANWRevFrance": dict(
        leader_history="Maximilien Robespierre (1758-1794), Jacobin lawyer and ideologue, dominated the Committee of Public Safety during the Reign of Terror until his own execution in Thermidor.",
        nation_history="The First French Republic (1792-1804) overthrew Bourbon monarchy, executed Louis XVI, levée-en-masse'd half a million conscripts, and exported Revolution at bayonet point.",
    ),
    "ANWNapoleonicFrance": dict(
        leader_history="Napoleon Bonaparte (1769-1821) crowned himself Emperor of the French in 1804 and conquered most of continental Europe before disastrous defeats in Russia (1812) and at Waterloo (1815).",
        nation_history="The French Empire welded the Revolution's reforms onto a centralised military meritocracy — Code Napoléon, the Grande Armée, and a Continental System aimed at strangling Britain.",
    ),
    "ANWCanadians": dict(
        leader_history="Louis-Joseph Papineau (1786-1871) led the Patriote movement in Lower Canada, demanding responsible government from the British colonial administration in the 1830s.",
        nation_history="The Province of Canada (1841-1867) merged Upper and Lower Canada after the 1837-1838 rebellions, paving the road toward Confederation and the Dominion of Canada.",
    ),
    "ANWFrenchCanadians": dict(
        leader_history="Louis Riel (1844-1885) led the Métis in the Red River Resistance and the North-West Rebellion, founding Manitoba before his execution by the Canadian government.",
        nation_history="Lower Canada was the French-speaking Catholic society of the St. Lawrence valley, anchored on the seigneurial system and the 1837 Patriote uprising for responsible government.",
    ),
    "ANWBrazil": dict(
        leader_history="Pedro II of Brazil (r. 1831-1889) reigned for 58 years over a constitutional monarchy that abolished slavery in 1888 — and was deposed by republican coup the following year.",
        nation_history="The Empire of Brazil (1822-1889) was the Americas' only durable post-colonial monarchy, fueled by sugar, coffee, and the Atlantic slave-trade until abolition forced political collapse.",
    ),
    "ANWArgentines": dict(
        leader_history="José de San Martín (1778-1850) led the Andean crossing of 1817 and liberated Chile and Peru from Spanish rule — refusing political office to die in self-imposed European exile.",
        nation_history="The Argentine Confederation grew from the Viceroyalty of the Río de la Plata into a federation of estancia provinces, dominated by the gaucho cavalry and the Buenos Aires merchant class.",
    ),
    "ANWChileans": dict(
        leader_history="Bernardo O'Higgins (1778-1842) co-led the Andean campaign with San Martín and served as Chile's Supreme Director (1817-1823), instituting the new republic's military and constitution.",
        nation_history="The Republic of Chile defended itself from royalist counter-attacks and, in the 1879-83 War of the Pacific, seized the nitrate-rich Atacama from Bolivia and Peru.",
    ),
    "ANWPeruvians": dict(
        leader_history="Andrés de Santa Cruz (1792-1865), Mestizo general and Peru-Bolivia Confederation founder, fought through Junín and Ayacucho in the wars of independence before the confederation collapsed in 1839.",
        nation_history="The Republic of Peru rose on Lima's wealth and Andean silver, lurched through caudillo wars, lost the War of the Pacific to Chile, and endured the long civilismo era.",
    ),
    "ANWColumbians": dict(
        leader_history="Simón Bolívar (1783-1830), El Libertador, freed six South American nations from Spain and dreamt the unfulfilled Gran Colombia — president of Venezuela, Peru, and the brief federation.",
        nation_history="Gran Colombia (1819-1831) bound modern Colombia, Venezuela, Ecuador and Panamá in Bolívar's federal vision before regional caudillos shattered it apart.",
    ),
    "ANWHaitians": dict(
        leader_history="Toussaint L'Ouverture (c.1743-1803), self-emancipated former slave, led the only successful slave revolution in modern history and effectively founded Haiti before dying in a Napoleonic prison.",
        nation_history="The First Empire of Haiti (1804) was the world's first Black-led republic born of the only successful slave revolt — a defiant anti-colonial state on the western third of Hispaniola.",
    ),
    "ANWIndonesians": dict(
        leader_history="Prince Diponegoro (1785-1855), Javanese aristocrat and Sufi mystic, led the 1825-30 Java War against Dutch colonial rule that killed perhaps 200,000 Javanese.",
        nation_history="The Sultanate of Yogyakarta — central court of Java — preserved royal Mataram-Sultanate culture under Dutch suzerainty, with kris, gamelan, and the dual sultan-and-pangeran nobility.",
    ),
    "ANWSouthAfricans": dict(
        leader_history="Paul Kruger (1825-1904), President of the South African Republic, led the Boers in the Second Boer War (1899-1902) against the British Empire before exile in Switzerland.",
        nation_history="The South African Republic (Transvaal) was a Boer pioneer state of trekkers, gold from Witwatersrand, and laagered ox-wagon defence — overrun by the British during the South African War.",
    ),
    "ANWFinnish": dict(
        leader_history="Carl Gustaf Mannerheim (1867-1951) — Tsarist general turned Finnish marshal — led the White army in the 1918 Civil War and the Finnish defence in the Winter and Continuation Wars.",
        nation_history="The Grand Duchy of Finland (1809-1917) was an autonomous Russian dominion that nurtured Finnish national identity through the Kalevala, Sibelius, and the eventual 1917 declaration of independence.",
    ),
    "ANWHungarians": dict(
        leader_history="Lajos Kossuth (1802-1894), governor-president of revolutionary Hungary in 1848-49, led the brief independence war against Habsburg Austria before defeat by Russian intervention.",
        nation_history="The Kingdom of Hungary endured Ottoman partition, Habsburg Compromise (1867), and the post-Trianon truncation — built on Magyar nobility, Pannonian agriculture, and the hussar tradition.",
    ),
    "ANWRomanians": dict(
        leader_history="Alexandru Ioan Cuza (1820-1873) merged Wallachia and Moldavia in 1859 to found the United Principalities, abolishing serfdom before his deposition by the Monstrous Coalition.",
        nation_history="The United Romanian Principalities became an independent kingdom in 1881 after the Russo-Turkish War, blending Latin Orthodox heritage with the Carpathian frontier.",
    ),
    "ANWBarbary": dict(
        leader_history="Hayreddin Barbarossa (c.1478-1546), Ottoman corsair turned Kapudan Pasha, ruled Algiers and commanded the imperial fleet's Mediterranean victories at Preveza and beyond.",
        nation_history="The Regency of Algiers and its Tripoli/Tunis sister-states were Ottoman corsair principalities — the Barbary States — raiding European shipping for slaves and tribute until the 19th century.",
    ),
    "ANWEgyptians": dict(
        leader_history="Muhammad Ali Pasha (r. 1805-1848), Albanian-Ottoman mercenary turned ruler, modernised Egypt with conscription, cotton, French advisors, and the elimination of the Mamluks at the Citadel massacre.",
        nation_history="The Khedivate of Egypt (1867-1914) was nominally Ottoman but built the Suez Canal, fielded a modern conscript army, and fell to British de-facto occupation after the 1882 Urabi revolt.",
    ),
    "ANWBajaCalifornians": dict(
        leader_history="Juan Bautista Alvarado (1809-1882), Californio governor, declared the short-lived 1836 Free State of Alta California — the seed of later northern Mexican autonomist movements.",
        nation_history="The Free State of Baja California sprang from Californio resistance to Mexican centralism — desert mission ranchos, vaquero cavalry, and pearl-fishing harbours from La Paz to San José.",
    ),
    "ANWMayans": dict(
        leader_history="Jacinto Pat and Cecilio Chi launched the 1847 Caste War — referenced here through Canek, the spirit of the Cruzob holy-cross movement that ruled rebel Maya territory until 1901.",
        nation_history="The Cruzob Maya state (1850-1901) of Chan Santa Cruz fought the Caste War against the Yucatec ladinos for over half a century — sustained by the Talking Cross oracle and British arms from Belize.",
    ),
    "ANWTexians": dict(
        leader_history="Sam Houston (1793-1863) defeated Santa Anna at San Jacinto in 1836 and twice served as President of the Republic of Texas before its annexation by the United States.",
        nation_history="The Republic of Texas (1836-1846) wrested independence from Mexico at San Jacinto and held a Lone Star nation across the Comanche frontier until annexation by the United States.",
    ),
}
