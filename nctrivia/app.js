// NC Bee Flashcards Application
// 180 Study Questions across 11 Categories

const QUESTIONS = [
  // Cities (14)
  {"id": 1, "category": "Cities", "q": "What is the largest city in NC?", "a": "Charlotte"},
  {"id": 2, "category": "Cities", "q": "What is the capital of NC?", "a": "Raleigh"},
  {"id": 3, "category": "Cities", "q": "Booker T. Washington called this place a “city of black enterprise and innovative black leaders.” What city was he talking about?", "a": "Durham"},
  {"id": 4, "category": "Cities", "q": "What city in NC is known for its high quality golf courses?", "a": "Pinehurst"},
  {"id": 5, "category": "Cities", "q": "What three cities make up the Triangle?", "a": "Raleigh, Durham, Chapel Hill"},
  {"id": 6, "category": "Cities", "q": "Name a major city in the mountains of NC.", "a": "Asheville, Boone, Hickory"},
  {"id": 7, "category": "Cities", "q": "Name 2 major cities in the piedmont of NC.", "a": "Raleigh, Durham, Charlotte, Greensboro, Winston-Salem"},
  {"id": 8, "category": "Cities", "q": "Name a major city in the sandhills of NC.", "a": "Pinehurst, Southern Pines, Fayetteville"},
  {"id": 9, "category": "Cities", "q": "Name a major city in the inner coastal plain of NC.", "a": "Greenville, Wilson, Kinston"},
  {"id": 10, "category": "Cities", "q": "Name a major city in the outer coastal plain of NC.", "a": "Wilmington, Morehead City, Jacksonville"},
  {"id": 11, "category": "Cities", "q": "Which region of the state has the largest number of big cities?", "a": "Piedmont"},
  {"id": 12, "category": "Cities", "q": "Who was the city of Raleigh named for?", "a": "Sir Walter Raleigh"},
  {"id": 13, "category": "Cities", "q": "Where did the name “Durham” come from?", "a": "Dr. Bartlett Durham, a landholder who gave the North Carolina Railroad Company his land, as a station for the new railroad."},
  {"id": 14, "category": "Cities", "q": "Who was North Carolina named for?", "a": "King Charles I and Charles II of England (“Carolinus” or “Carolus” means Charles in Latin.)"},

  // State Symbols (30)
  {"id": 15, "category": "State Symbols", "q": "What is the state bird?", "a": "Cardinal"},
  {"id": 16, "category": "State Symbols", "q": "What is the state mammal?", "a": "Eastern Gray Squirrel"},
  {"id": 17, "category": "State Symbols", "q": "What is the state marsupial?", "a": "Virginia Opossum"},
  {"id": 18, "category": "State Symbols", "q": "What is the state dog?", "a": "Plott Hound"},
  {"id": 19, "category": "State Symbols", "q": "What is the state horse?", "a": "Spanish Mustang (Wild Ponies of Outer Banks)"},
  {"id": 20, "category": "State Symbols", "q": "What is the state reptile?", "a": "Eastern Box Turtle"},
  {"id": 21, "category": "State Symbols", "q": "What is the state saltwater fish?", "a": "Channel Bass (aka Red Drum)"},
  {"id": 22, "category": "State Symbols", "q": "What is the state freshwater fish?", "a": "Southern Appalachian Brook Trout"},
  {"id": 23, "category": "State Symbols", "q": "What is the state salamander?", "a": "Marbled Salamander"},
  {"id": 24, "category": "State Symbols", "q": "What is the state frog?", "a": "Pine Barrens Tree Frog"},
  {"id": 25, "category": "State Symbols", "q": "What is the state insect?", "a": "Honey Bee"},
  {"id": 26, "category": "State Symbols", "q": "What is the state beverage?", "a": "Milk"},
  {"id": 27, "category": "State Symbols", "q": "What is the state vegetable?", "a": "Sweet Potato"},
  {"id": 28, "category": "State Symbols", "q": "What are the state berries?", "a": "Strawberry and Blueberry"},
  {"id": 29, "category": "State Symbols", "q": "What is the state fruit?", "a": "Scuppernong Grapes"},
  {"id": 30, "category": "State Symbols", "q": "What is the state flower?", "a": "Dogwood"},
  {"id": 31, "category": "State Symbols", "q": "What is the state wildflower?", "a": "Carolina Lily"},
  {"id": 32, "category": "State Symbols", "q": "What is the state carnivorous plant?", "a": "Venus Flytrap"},
  {"id": 33, "category": "State Symbols", "q": "What is the state tree?", "a": "Longleaf Pine"},
  {"id": 34, "category": "State Symbols", "q": "What are the state nicknames?", "a": "Old North State, North Cackalacky, Tar Heel State"},
  {"id": 35, "category": "State Symbols", "q": "What are the state colors?", "a": "Red, Blue"},
  {"id": 36, "category": "State Symbols", "q": "What is the state motto?", "a": "Esse quam Videri (To Be Rather than to Seem)"},
  {"id": 37, "category": "State Symbols", "q": "What is the state rock?", "a": "Granite"},
  {"id": 38, "category": "State Symbols", "q": "What is the state mineral?", "a": "Gold"},
  {"id": 39, "category": "State Symbols", "q": "What is the state gemstone?", "a": "Emerald"},
  {"id": 40, "category": "State Symbols", "q": "What is the state fossil?", "a": "Megalodon tooth"},
  {"id": 41, "category": "State Symbols", "q": "What is the state shell?", "a": "Scotch Bonnet"},
  {"id": 42, "category": "State Symbols", "q": "What is the state boat?", "a": "Shad Boat"},
  {"id": 43, "category": "State Symbols", "q": "What are the state dances?", "a": "Clogging, Shag"},
  {"id": 44, "category": "State Symbols", "q": "What is the State toast?", "a": "Here’s to the land of the Long Leaf Pine..."},

  // Geography/Landforms (22)
  {"id": 45, "category": "Geography & Landforms", "q": "Which state lies North of NC?", "a": "Virginia"},
  {"id": 46, "category": "Geography & Landforms", "q": "Which body of water lies East of NC?", "a": "Atlantic Ocean"},
  {"id": 47, "category": "Geography & Landforms", "q": "Which states lie South of NC?", "a": "South Carolina, Georgia"},
  {"id": 48, "category": "Geography & Landforms", "q": "Which state lies West of NC?", "a": "Tennessee"},
  {"id": 49, "category": "Geography & Landforms", "q": "What is the name of the entire mountain range that goes through NC and on up the east coast of the US?", "a": "The Appalachian Mountains"},
  {"id": 50, "category": "Geography & Landforms", "q": "Within the Appalachian Mountains, there are several smaller ranges in our state. Name one.", "a": "Blue Ridge Mountains, Great Smoky Mountains, Pisgah Mountains, Saura Mountains, Uwharrie Mountains"},
  {"id": 51, "category": "Geography & Landforms", "q": "What is the tallest mountain on the east coast, located in NC?", "a": "Mt. Mitchell"},
  {"id": 52, "category": "Geography & Landforms", "q": "What is Mt. Mitchell’s elevation?", "a": "6,684 feet"},
  {"id": 53, "category": "Geography & Landforms", "q": "Name a monadnock located in NC.", "a": "Hanging Rock, Pilot Mountain, Stone Mountain, Crowders Mountain"},
  {"id": 54, "category": "Geography & Landforms", "q": "What is the name of the string of barrier islands off the mainland of NC?", "a": "Outer Banks"},
  {"id": 55, "category": "Geography & Landforms", "q": "What are the marshy, round, natural lakes found in the inner coastal plain of NC called?", "a": "Pocosins"},
  {"id": 56, "category": "Geography & Landforms", "q": "What is the name of the largest natural lake in NC?", "a": "Lake Mattamuskeet"},
  {"id": 57, "category": "Geography & Landforms", "q": "Name the larger of the two immense sounds in NC.", "a": "Pamlico Sound"},
  {"id": 58, "category": "Geography & Landforms", "q": "Name the smaller of the two immense sounds in NC.", "a": "Albemarle Sound"},
  {"id": 59, "category": "Geography & Landforms", "q": "Name the longest river entirely in NC.", "a": "Neuse River"},
  {"id": 60, "category": "Geography & Landforms", "q": "Name the largest river basin contained in N.C.", "a": "Cape Fear River Basin"},
  {"id": 61, "category": "Geography & Landforms", "q": "Where did the Eno River get its name?", "a": "From the Eno Indians who lived along its banks"},
  {"id": 62, "category": "Geography & Landforms", "q": "Name the three main regions of NC.", "a": "Mountains, Piedmont, and Coastal Plain"},
  {"id": 63, "category": "Geography & Landforms", "q": "What does the word “piedmont” mean?", "a": "Foot of the mountain or foot hills"},
  {"id": 64, "category": "Geography & Landforms", "q": "What was the largest swamp located in NC?", "a": "The Great Dismal Swamp"},
  {"id": 65, "category": "Geography & Landforms", "q": "How many counties are in North Carolina?", "a": "100"},
  {"id": 66, "category": "Geography & Landforms", "q": "NC has what is believed to be the second oldest river on Earth. What is the name of this river?", "a": "The New River"},

  // Points of Interest (12)
  {"id": 67, "category": "Points of Interest", "q": "How many lighthouses are located on the Outer Banks of NC?", "a": "Seven"},
  {"id": 68, "category": "Points of Interest", "q": "Why are there so many lighthouses along our coast?", "a": "To warn ships about our dangerous coastline with sand bars and shallow water"},
  {"id": 69, "category": "Points of Interest", "q": "What is the largest cave system open to the public that is located in NC?", "a": "Linville Caverns"},
  {"id": 70, "category": "Points of Interest", "q": "What is the name of the largest moving sand dune on the Outer Banks of NC?", "a": "Jockey’s Ridge"},
  {"id": 71, "category": "Points of Interest", "q": "Name the Army base near Fayetteville, NC.", "a": "Fort Liberty"},
  {"id": 72, "category": "Points of Interest", "q": "What is the main port city in NC?", "a": "Wilmington"},
  {"id": 73, "category": "Points of Interest", "q": "What Monument is located in Kitty Hawk, NC?", "a": "Wright Brothers Memorial"},
  {"id": 74, "category": "Points of Interest", "q": "Where can you walk across a mile high swinging bridge?", "a": "Grandfather Mountain"},
  {"id": 75, "category": "Points of Interest", "q": "What is the name of one of the only “Old Growth” Forests (the trees there have NEVER been cut)?", "a": "Joyce Kilmer Forest"},
  {"id": 76, "category": "Points of Interest", "q": "What is the largest amusement park in NC?", "a": "Carowinds"},
  {"id": 77, "category": "Points of Interest", "q": "How many NC state parks are there?", "a": "41"},
  {"id": 78, "category": "Points of Interest", "q": "What is the name of the largest mansion in the United States, built by George Vanderbilt, and located in Asheville, NC?", "a": "Biltmore Estate"},

  // History (40)
  {"id": 79, "category": "History", "q": "Name one of the US Presidents from NC.", "a": "James K. Polk, Andrew Jackson, Andrew Johnson"},
  {"id": 80, "category": "History", "q": "Name 3 Native American Tribes who have lived in NC.", "a": "Cherokee, Lumbee, Saura, Catawba, Roanoke, Croatoan, Occaneechi, Saponi, Hiawassee, Tuscarora, Iroquois, Waccamaw-Siouan, Algonquian, Coharie, Meherrin, Haliwa-Saponi"},
  {"id": 81, "category": "History", "q": "Name either the Roanoke or Croatan chief who went to England with John White as ambassadors to meet Queen Elizabeth I.", "a": "Wanchese or Manteo"},
  {"id": 82, "category": "History", "q": "About how many years had the native indigenous people (Native Americans) lived on the land now called North Carolina BEFORE the Europeans invaded?", "a": "12,000 years"},
  {"id": 83, "category": "History", "q": "How many native indigenous people were living on NC land in 1550, before the Europeans arrived?", "a": "More than 100,000"},
  {"id": 84, "category": "History", "q": "Who did Queen Elizabeth I select to establish an English colony in North America?", "a": "Sir Walter Raleigh"},
  {"id": 85, "category": "History", "q": "Name one of the Native Americans who helped the early settlers from England survive.", "a": "Manteo, Wanchese"},
  {"id": 86, "category": "History", "q": "What was the nickname of the English Colony established on Roanoke Island?", "a": "The Lost Colony"},
  {"id": 87, "category": "History", "q": "In the 1840s the Cherokee were forced to leave NC by the US government. What was this called?", "a": "The Trail of Tears"},
  {"id": 88, "category": "History", "q": "Who was the first English child born in the “New World”?", "a": "Virginia Dare"},
  {"id": 89, "category": "History", "q": "What did the Wright Brothers accomplish in 1903?", "a": "Powered Air Flight"},
  {"id": 90, "category": "History", "q": "Where was gold first found in the United States?", "a": "Reed Gold Mine in NC"},
  {"id": 91, "category": "History", "q": "What was the CCC?", "a": "Civilian Conservation Corps"},
  {"id": 92, "category": "History", "q": "In 1795, this was the first public university opened in the United States.", "a": "UNC - Chapel Hill"},
  {"id": 93, "category": "History", "q": "This Greensboro college started out in 1873 as a school where freed slaves could learn, then in 1926 it became a black women’s college. What is its name?", "a": "Bennett College"},
  {"id": 94, "category": "History", "q": "In 1865, this was the first historically black university created in NC.", "a": "Shaw University"},
  {"id": 95, "category": "History", "q": "This historically black university located in Durham was opened in 1910.", "a": "NC Central University"},
  {"id": 96, "category": "History", "q": "What was the first capital of NC in 1722?", "a": "Edenton"},
  {"id": 97, "category": "History", "q": "What city was chosen as the second capital of NC in 1771?", "a": "New Bern"},
  {"id": 98, "category": "History", "q": "What city was chosen as the current capital of NC in 1792?", "a": "Raleigh"},
  {"id": 99, "category": "History", "q": "What Italian explorer visited the NC coast in 1524?", "a": "Giovanni Verrazano"},
  {"id": 100, "category": "History", "q": "In 1540, what Spanish explorer came looking for gold in NC?", "a": "Hernando de Soto"},
  {"id": 101, "category": "History", "q": "This 26 year old Englishman explored the back country of NC, and founded the city of Bath.", "a": "John Lawson"},
  {"id": 102, "category": "History", "q": "There are 2 dates on the NC flag. Name one of the events that took place on one of those dates.", "a": "Halifax Resolves, Mecklenburg Declaration of Independence"},
  {"id": 103, "category": "History", "q": "This set of laws enacted in the 1880s legalized segregation, especially in education and on public transportation.", "a": "Jim Crow laws"},
  {"id": 104, "category": "History", "q": "In 1898, John Merrick founded the North Carolina Mutual Insurance Company. This was the largest African American owned company in America. Where is it located?", "a": "Durham"},
  {"id": 105, "category": "History", "q": "What Durham architect designed the Bulls ballpark, 3 Durham libraries, and the Museum of African American History in Washington DC?", "a": "Phil Freelon"},
  {"id": 106, "category": "History", "q": "Who was the NC Governor that was well known for improving schools and starting the Research Triangle Park?", "a": "Terry Sanford"},
  {"id": 107, "category": "History", "q": "What was the reason for the Greensboro Sit-Ins that happened in 1960?", "a": "Civil Rights Protests to End Racial Discrimination"},
  {"id": 108, "category": "History", "q": "In what year did the Royal Ice Cream Sit-in happen in Durham?", "a": "1957"},
  {"id": 109, "category": "History", "q": "Who was the black woman born in 1818, who was a seamstress, activist, and writer? She was even the personal dressmaker for Mary Todd Lincoln.", "a": "Elizabeth Keckley"},
  {"id": 110, "category": "History", "q": "What religious group bought a large tract of land called Wachovia in the Piedmont?", "a": "The Moravians"},
  {"id": 111, "category": "History", "q": "Who built Hanging Rock State Park, the Blue Ridge Parkway, Pilot Mountain, and many other parks in the state?", "a": "Civilian Conservation Corps (CCC)"},
  {"id": 112, "category": "History", "q": "Who was the most famous pirate to inhabit the NC islands?", "a": "Blackbeard, or Edward Teach"},
  {"id": 113, "category": "History", "q": "Who was the most famous female pirate in NC?", "a": "Anne Bonny"},
  {"id": 114, "category": "History", "q": "Why were there so many pirates that worked or lived around the Coast of NC?", "a": "1) Because of all the islands and inlets to hide from the law, and 2) the Outer Banks were dangerous for ships, and made it easier for pirates to attack."},
  {"id": 115, "category": "History", "q": "Which Cherokee leader created a written language?", "a": "Sequoyah"},
  {"id": 116, "category": "History", "q": "What type of home did the coastal tribes of North Carolina build?", "a": "Longhouse"},
  {"id": 117, "category": "History", "q": "Which Native American group lived in the mountain region?", "a": "Cherokee"},
  {"id": 118, "category": "History", "q": "What did Ralph Fessenden use to communicate from the Outer Banks for the first time in 1902?", "a": "Telegraph"},

  // Plants of NC (6)
  {"id": 119, "category": "Plants of NC", "q": "What carnivorous plant only grows natively in coastal areas of NC and SC?", "a": "Venus Flytrap"},
  {"id": 120, "category": "Plants of NC", "q": "What is another carnivorous plant that grows in NC?", "a": "Pitcher Plant, Sundew, Butterwort, Bladderwort"},
  {"id": 121, "category": "Plants of NC", "q": "What tree was used for making pitch and tar during colonial times?", "a": "Longleaf Pine"},
  {"id": 122, "category": "Plants of NC", "q": "Name one of the poisonous vines found in NC.", "a": "Poison Ivy, Poison Oak"},
  {"id": 123, "category": "Plants of NC", "q": "Name a common deciduous tree native to NC.", "a": "Maple, Oak, Elm, Sycamore, Sweetgum, Hickory, Beech"},
  {"id": 124, "category": "Plants of NC", "q": "Name a common coniferous tree native to NC.", "a": "Pine, Fir, Cedar, Spruce"},

  // Animals of NC (9)
  {"id": 125, "category": "Animals of NC", "q": "What is the largest mammal that lives in both the mountains and the coastal plain areas of NC?", "a": "Black Bear"},
  {"id": 126, "category": "Animals of NC", "q": "What herd animal is overpopulating our state?", "a": "White Tailed Deer"},
  {"id": 127, "category": "Animals of NC", "q": "The Smoky Mountains of NC have more species of these animals than any other place in the world!", "a": "Salamanders"},
  {"id": 128, "category": "Animals of NC", "q": "Where is the NC Zoo located?", "a": "Asheboro, NC"},
  {"id": 129, "category": "Animals of NC", "q": "What makes the NC Zoo special?", "a": "It has larger habitat spaces for the animals, and is the largest walk-through zoo in the world."},
  {"id": 130, "category": "Animals of NC", "q": "A NC study has shown that there are about 124 million of this type of animal for every acre of NC land.", "a": "Insects"},
  {"id": 131, "category": "Animals of NC", "q": "These turtles lay their eggs on NC beaches between April and September each year.", "a": "Loggerhead Turtles"},
  {"id": 132, "category": "Animals of NC", "q": "How many species of animals and plants are threatened or endangered in NC?", "a": "401 (239 animals & 162 plants)"},
  {"id": 133, "category": "Animals of NC", "q": "What is the canid species native to North Carolina that is endangered, and only 20-25 still exist in the wild?", "a": "Canis Rufus (red wolf)"},

  // Agriculture (11)
  {"id": 134, "category": "Agriculture", "q": "Which region of NC has the most farming?", "a": "Inner Coastal Plain"},
  {"id": 135, "category": "Agriculture", "q": "NC is the Number 1 producer of this orange root vegetable.", "a": "Sweet Potatoes"},
  {"id": 136, "category": "Agriculture", "q": "NC is the Number 1 producer of this leafy plant used in cigarettes and cigars.", "a": "Tobacco"},
  {"id": 137, "category": "Agriculture", "q": "NC is one of the leading producers of these poultry products.", "a": "Chickens and eggs"},
  {"id": 138, "category": "Agriculture", "q": "NC is the 2nd largest producer of this large edible holiday bird.", "a": "Turkeys"},
  {"id": 139, "category": "Agriculture", "q": "NC is the 2nd largest producer of this holiday forest product.", "a": "Christmas Trees"},
  {"id": 140, "category": "Agriculture", "q": "NC is the 2nd largest producer of this freshwater fish.", "a": "Trout"},
  {"id": 141, "category": "Agriculture", "q": "NC is the 2nd largest producer of pork, which comes from this animal.", "a": "Pigs/Hogs"},
  {"id": 142, "category": "Agriculture", "q": "NC is the 3rd largest producer of this vegetable used for making pickles.", "a": "Cucumbers"},
  {"id": 143, "category": "Agriculture", "q": "What is the largest fruit crop grown in NC?", "a": "Apples or Peaches"},
  {"id": 144, "category": "Agriculture", "q": "What plant for making cloth is grown in NC?", "a": "Cotton"},

  // Industry/Manufacturing (10)
  {"id": 145, "category": "Industry & Manufacturing", "q": "What industry in NC makes use of the trees that grow in our state?", "a": "Furniture making"},
  {"id": 146, "category": "Industry & Manufacturing", "q": "What NC industry makes clothing, material, and linens?", "a": "Textile"},
  {"id": 147, "category": "Industry & Manufacturing", "q": "What is manufactured using the clay and sand found in our state?", "a": "Bricks"},
  {"id": 148, "category": "Industry & Manufacturing", "q": "What industry is created from all the visitors that travel around our beautiful state?", "a": "Tourism"},
  {"id": 149, "category": "Industry & Manufacturing", "q": "What industry uses cameras to record stories and scenery in NC?", "a": "Film or Movie Making Industry"},
  {"id": 150, "category": "Industry & Manufacturing", "q": "What industry uses living organisms to make medicines?", "a": "Biotechnology"},
  {"id": 151, "category": "Industry & Manufacturing", "q": "Granite, Feldspar and Phosphate are all products of this industry.", "a": "Mining"},
  {"id": 152, "category": "Industry & Manufacturing", "q": "Catfish, crabs, flounder and shrimp are all products of this watery industry.", "a": "Fishing"},
  {"id": 153, "category": "Industry & Manufacturing", "q": "Cisco, SAS, and Google all help make NC the second fastest growing state for this industry.", "a": "Information Technology (IT)"},
  {"id": 154, "category": "Industry & Manufacturing", "q": "NC is the 3rd largest state for this money-based industry.", "a": "Banking and Finance"},

  // The Arts (18)
  {"id": 155, "category": "The Arts", "q": "Who is Thelonious Monk?", "a": "A famous modern jazz piano player and composer from NC"},
  {"id": 156, "category": "The Arts", "q": "This NC jazz saxophonist and composer worked with Thelonious Monk.", "a": "John Coltrane"},
  {"id": 157, "category": "The Arts", "q": "James Taylor is a famous folk singer from what NC town?", "a": "Chapel Hill"},
  {"id": 158, "category": "The Arts", "q": "Who was the award winning bluegrass and traditional mountain music guitar player and singer who became blind when he was an infant?", "a": "Doc Watson"},
  {"id": 159, "category": "The Arts", "q": "Name a famous Jazz musician from NC.", "a": "Thelonious Monk, Nina Simone, John Coltrane"},
  {"id": 160, "category": "The Arts", "q": "Name a famous Old Time/Country musician from NC.", "a": "Earl Scruggs, Arthur Smith, Doc Watson, Del McCoury"},
  {"id": 161, "category": "The Arts", "q": "Name a famous Piedmont Blues musician from NC.", "a": "Blind Boy Fuller, Elizabeth Cotten, Etta Baker"},
  {"id": 162, "category": "The Arts", "q": "What type of music did Elizabeth Cotten play and sing?", "a": "The Blues"},
  {"id": 163, "category": "The Arts", "q": "Name one of the American Idol winners who came from NC.", "a": "Fantasia, Scotty McCreery, Caleb Johnson"},
  {"id": 164, "category": "The Arts", "q": "Why is NC such a great state for making pottery?", "a": "We have a lot of quality clay in the Piedmont"},
  {"id": 165, "category": "The Arts", "q": "What are the two methods Natives used for making pots?", "a": "Coil and Pinch pots"},
  {"id": 166, "category": "The Arts", "q": "What NC town, located near Asheboro, is the “handmade pottery capital of the US”?", "a": "Seagrove"},
  {"id": 167, "category": "The Arts", "q": "This famous NC artist used collage to create vivid snippets of African American life in the South.", "a": "Romare Bearden"},
  {"id": 168, "category": "The Arts", "q": "Who was the lead actor in a classic TV comedy show set in Mayberry NC?", "a": "Andy Griffith"},
  {"id": 169, "category": "The Arts", "q": "This person was a Pulitzer Prize-winning playwright from NC, and author of The Lost Colony outdoor play.", "a": "Paul Green"},
  {"id": 170, "category": "The Arts", "q": "This dance group, founded by Chuck Davis in Durham, performs and celebrates traditional African Dance.", "a": "The African American Dance Ensemble"},
  {"id": 171, "category": "The Arts", "q": "What is Clogging?", "a": "A NC Appalachian Mountain music dance"},
  {"id": 172, "category": "The Arts", "q": "What is the Shag?", "a": "A NC beach music dance"},

  // NC Government (8)
  {"id": 173, "category": "NC Government", "q": "What are the three branches of state government?", "a": "Executive, Legislative, and Judicial"},
  {"id": 174, "category": "NC Government", "q": "Which branch includes the Governor?", "a": "Executive"},
  {"id": 175, "category": "NC Government", "q": "Which branch makes the laws for our state?", "a": "Legislative"},
  {"id": 176, "category": "NC Government", "q": "Which branch is made up of judges and courts?", "a": "Judicial"},
  {"id": 177, "category": "NC Government", "q": "The group of people in the Legislative branch are also called the General Assembly. What are the two houses in the General Assembly called?", "a": "The House of Representatives and the Senate"},
  {"id": 178, "category": "NC Government", "q": "What kind of government do we have - Monarchy, Democracy, or Dictatorship?", "a": "Democracy"},
  {"id": 179, "category": "NC Government", "q": "What are two ways everyone in our state can participate in our democracy?", "a": "Vote, Help a candidate get elected, Protest about something you want changed, Be an activist or community organizer"},
  {"id": 180, "category": "NC Government", "q": "Who is the current governor of NC?", "a": "Josh Stein"}
];

// App State
let state = {
  mode: 'flashcard', // 'flashcard' | 'quiz' | 'guide'
  selectedCategory: 'all',
  statusFilter: 'all', // 'all' | 'unmastered' | 'mastered' | 'starred'
  searchQuery: '',
  currentIndex: 0,
  isFlipped: false,
  isShuffled: false,
  filteredDeck: [],
  mastered: new Set(),
  starred: new Set(),
  // Quiz state
  quizDeck: [],
  quizIndex: 0,
  quizScore: 0,
  quizTotal: 0,
  quizAnswered: false
};

// Storage Keys
const STORAGE_KEY = 'nc_trivia_bee_flashcards_v1';

function loadPersistedData() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const data = JSON.parse(raw);
      if (Array.isArray(data.mastered)) state.mastered = new Set(data.mastered);
      if (Array.isArray(data.starred)) state.starred = new Set(data.starred);
    }
  } catch (e) {
    console.error('Failed to load storage:', e);
  }
}

function savePersistedData() {
  try {
    const payload = {
      mastered: Array.from(state.mastered),
      starred: Array.from(state.starred)
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (e) {
    console.error('Failed to save storage:', e);
  }
}

// Categories list
const CATEGORIES = Array.from(new Set(QUESTIONS.map(q => q.category)));

function init() {
  loadPersistedData();
  initTheme();
  setupCategorySelect();
  applyFilters();
  setupEventListeners();
  updateStats();
  renderCurrentMode();
}

function initTheme() {
  const savedTheme = localStorage.getItem('nc_trivia_theme') || 
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('nc_trivia_theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
}

function setupCategorySelect() {
  const select = document.getElementById('category-select');
  if (!select) return;
  select.innerHTML = `<option value="all">All Categories (${QUESTIONS.length})</option>`;
  CATEGORIES.forEach(cat => {
    const count = QUESTIONS.filter(q => q.category === cat).length;
    const opt = document.createElement('option');
    opt.value = cat;
    opt.textContent = `${cat} (${count})`;
    select.appendChild(opt);
  });
}

function applyFilters() {
  let deck = QUESTIONS.filter(item => {
    // Category match
    if (state.selectedCategory !== 'all' && item.category !== state.selectedCategory) {
      return false;
    }
    // Status filter
    if (state.statusFilter === 'mastered' && !state.mastered.has(item.id)) {
      return false;
    }
    if (state.statusFilter === 'unmastered' && state.mastered.has(item.id)) {
      return false;
    }
    if (state.statusFilter === 'starred' && !state.starred.has(item.id)) {
      return false;
    }
    // Search query match
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      const matchQ = item.q.toLowerCase().includes(q);
      const matchA = item.a.toLowerCase().includes(q);
      const matchC = item.category.toLowerCase().includes(q);
      if (!matchQ && !matchA && !matchC) return false;
    }
    return true;
  });

  if (state.isShuffled) {
    deck = shuffleArray([...deck]);
  }

  state.filteredDeck = deck;
  if (state.currentIndex >= state.filteredDeck.length) {
    state.currentIndex = Math.max(0, state.filteredDeck.length - 1);
  }
  state.isFlipped = false;
  updateStats();
}

function shuffleArray(arr) {
  const res = [...arr];
  for (let i = res.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [res[i], res[j]] = [res[j], res[i]];
  }
  return res;
}

function updateStats() {
  const total = QUESTIONS.length;
  const masteredCount = state.mastered.size;
  const percent = Math.round((masteredCount / total) * 100);

  const fillEl = document.getElementById('progress-fill');
  const statsEl = document.getElementById('progress-stats');
  if (fillEl) fillEl.style.width = `${percent}%`;
  if (statsEl) statsEl.textContent = `${masteredCount} / ${total} Mastered (${percent}%)`;

  // Update filter pill counts
  const allCount = document.getElementById('count-all');
  const unmasteredCount = document.getElementById('count-unmastered');
  const masteredPillCount = document.getElementById('count-mastered');
  const starredCount = document.getElementById('count-starred');

  if (allCount) allCount.textContent = QUESTIONS.length;
  if (unmasteredCount) unmasteredCount.textContent = QUESTIONS.length - state.mastered.size;
  if (masteredPillCount) masteredPillCount.textContent = state.mastered.size;
  if (starredCount) starredCount.textContent = state.starred.size;
}

function renderCurrentMode() {
  const flashcardSec = document.getElementById('flashcard-section');
  const quizSec = document.getElementById('quiz-section');
  const guideSec = document.getElementById('guide-section');

  if (flashcardSec) flashcardSec.style.display = state.mode === 'flashcard' ? 'block' : 'none';
  if (quizSec) quizSec.style.display = state.mode === 'quiz' ? 'block' : 'none';
  if (guideSec) guideSec.style.display = state.mode === 'guide' ? 'block' : 'none';

  if (state.mode === 'flashcard') {
    renderFlashcard();
  } else if (state.mode === 'quiz') {
    startQuiz();
  } else if (state.mode === 'guide') {
    renderGuide();
  }
}

// Flashcard Renderer
function renderFlashcard() {
  const cardScene = document.getElementById('card-scene');
  const emptyScene = document.getElementById('empty-scene');
  const actionsBar = document.getElementById('card-actions');
  const kbdBar = document.getElementById('keyboard-hint');

  if (state.filteredDeck.length === 0) {
    if (cardScene) cardScene.style.display = 'none';
    if (actionsBar) actionsBar.style.display = 'none';
    if (kbdBar) kbdBar.style.display = 'none';
    if (emptyScene) emptyScene.style.display = 'block';
    return;
  }

  if (cardScene) cardScene.style.display = 'block';
  if (actionsBar) actionsBar.style.display = 'flex';
  if (kbdBar) kbdBar.style.display = 'block';
  if (emptyScene) emptyScene.style.display = 'none';

  const card = state.filteredDeck[state.currentIndex];
  const cardEl = document.getElementById('flashcard');

  // Set flip state
  if (cardEl) {
    if (state.isFlipped) {
      cardEl.classList.add('is-flipped');
    } else {
      cardEl.classList.remove('is-flipped');
    }
  }

  // Populate content
  const qEl = document.getElementById('card-question');
  const aEl = document.getElementById('card-answer');
  const catEl = document.getElementById('card-category');
  const catBackEl = document.getElementById('card-category-back');
  const numEl = document.getElementById('card-number');
  const starBtn = document.getElementById('btn-star');

  if (qEl) qEl.textContent = card.q;
  if (aEl) aEl.textContent = card.a;
  if (catEl) catEl.textContent = card.category;
  if (catBackEl) catBackEl.textContent = card.category;
  if (numEl) numEl.textContent = `${state.currentIndex + 1} of ${state.filteredDeck.length}`;

  const isStarred = state.starred.has(card.id);
  if (starBtn) {
    starBtn.innerHTML = isStarred ? '★' : '☆';
    starBtn.classList.toggle('starred', isStarred);
    starBtn.title = isStarred ? 'Starred (Click to unstar)' : 'Star question (S)';
  }

  // Update navigation buttons
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  if (prevBtn) prevBtn.disabled = state.currentIndex === 0;
  if (nextBtn) nextBtn.disabled = state.currentIndex === state.filteredDeck.length - 1;
}

function flipCard() {
  state.isFlipped = !state.isFlipped;
  const cardEl = document.getElementById('flashcard');
  if (cardEl) {
    cardEl.classList.toggle('is-flipped', state.isFlipped);
  }
}

function nextCard() {
  if (state.currentIndex < state.filteredDeck.length - 1) {
    state.currentIndex++;
    state.isFlipped = false;
    renderFlashcard();
  }
}

function prevCard() {
  if (state.currentIndex > 0) {
    state.currentIndex--;
    state.isFlipped = false;
    renderFlashcard();
  }
}

function markCard(mastered) {
  if (state.filteredDeck.length === 0) return;
  const card = state.filteredDeck[state.currentIndex];
  if (mastered) {
    state.mastered.add(card.id);
  } else {
    state.mastered.delete(card.id);
  }
  savePersistedData();
  updateStats();

  // If we are filtering by unmastered/mastered, reapply filters
  if (state.statusFilter === 'unmastered' || state.statusFilter === 'mastered') {
    applyFilters();
    renderFlashcard();
  } else {
    // Automatically advance to next card if available
    if (state.currentIndex < state.filteredDeck.length - 1) {
      nextCard();
    }
  }
}

function toggleStarCurrent() {
  if (state.filteredDeck.length === 0) return;
  const card = state.filteredDeck[state.currentIndex];
  if (state.starred.has(card.id)) {
    state.starred.delete(card.id);
  } else {
    state.starred.add(card.id);
  }
  savePersistedData();
  updateStats();
  renderFlashcard();
}

// Text-to-Speech
function speakCurrent() {
  if (!('speechSynthesis' in window)) {
    alert('Speech synthesis is not supported in this browser.');
    return;
  }
  if (state.filteredDeck.length === 0) return;
  window.speechSynthesis.cancel();
  const card = state.filteredDeck[state.currentIndex];
  const text = state.isFlipped ? `The answer is: ${card.a}` : card.q;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 1.0;
  window.speechSynthesis.speak(utterance);
}

// Quiz Mode Implementation
function startQuiz() {
  let deck = [...state.filteredDeck];
  if (deck.length === 0) deck = [...QUESTIONS];
  state.quizDeck = shuffleArray(deck);
  state.quizIndex = 0;
  state.quizScore = 0;
  state.quizTotal = Math.min(25, state.quizDeck.length);
  renderQuizQuestion();
}

function renderQuizQuestion() {
  const container = document.getElementById('quiz-container');
  if (!container) return;

  if (state.quizIndex >= state.quizTotal) {
    // Quiz finished screen
    const pct = Math.round((state.quizScore / state.quizTotal) * 100);
    container.innerHTML = `
      <div style="text-align: center; padding: 2rem 1rem;">
        <div style="font-size: 3rem; margin-bottom: 1rem;">🎉</div>
        <h2 style="font-size: 1.8rem; margin-bottom: 0.5rem; color: var(--text-primary);">Quiz Complete!</h2>
        <p style="font-size: 1.25rem; color: var(--carolina-blue); font-weight: 700; margin-bottom: 1.5rem;">
          You scored ${state.quizScore} out of ${state.quizTotal} (${pct}%)
        </p>
        <p style="color: var(--text-secondary); margin-bottom: 2rem;">
          ${pct >= 90 ? 'Outstanding! You are a North Carolina trivia master!' : pct >= 70 ? 'Great job! Keep reviewing to get 100%!' : 'Good practice! Review the flashcards to boost your score!'}
        </p>
        <button id="btn-restart-quiz" class="btn-flip" style="max-width: 260px; margin: 0 auto;">Take Another Quiz</button>
      </div>
    `;
    document.getElementById('btn-restart-quiz')?.addEventListener('click', startQuiz);
    return;
  }

  const current = state.quizDeck[state.quizIndex];
  state.quizAnswered = false;

  // Generate 3 distractors from same category or random
  let pool = QUESTIONS.filter(q => q.id !== current.id && q.category === current.category);
  if (pool.length < 3) {
    pool = QUESTIONS.filter(q => q.id !== current.id);
  }
  const distractors = shuffleArray(pool).slice(0, 3).map(q => q.a);
  const options = shuffleArray([current.a, ...distractors]);

  container.innerHTML = `
    <div class="quiz-header">
      <div class="category-tag">${current.category}</div>
      <div class="quiz-score-badge">Question ${state.quizIndex + 1} of ${state.quizTotal} | Score: ${state.quizScore}</div>
    </div>
    <div class="quiz-question-box">
      <div class="quiz-question-text">${current.q}</div>
    </div>
    <div class="quiz-options-list" id="quiz-options">
      ${options.map((opt, idx) => `
        <button class="quiz-option-btn" data-option="${encodeURIComponent(opt)}">
          <span class="quiz-option-letter">${String.fromCharCode(65 + idx)}</span>
          <span>${opt}</span>
        </button>
      `).join('')}
    </div>
    <div class="quiz-feedback" id="quiz-feedback"></div>
    <button class="quiz-next-btn" id="btn-quiz-next">Next Question →</button>
  `;

  // Option click handlers
  const optBtns = container.querySelectorAll('.quiz-option-btn');
  optBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (state.quizAnswered) return;
      state.quizAnswered = true;
      const selected = decodeURIComponent(btn.getAttribute('data-option'));
      const isCorrect = selected === current.a;

      const feedback = document.getElementById('quiz-feedback');
      const nextBtn = document.getElementById('btn-quiz-next');

      optBtns.forEach(b => {
        b.disabled = true;
        const optVal = decodeURIComponent(b.getAttribute('data-option'));
        if (optVal === current.a) {
          b.classList.add('selected-correct');
        } else if (optVal === selected && !isCorrect) {
          b.classList.add('selected-wrong');
        }
      });

      if (isCorrect) {
        state.quizScore++;
        state.mastered.add(current.id);
        savePersistedData();
        updateStats();
        feedback.className = 'quiz-feedback show correct';
        feedback.innerHTML = `<strong>✓ Correct!</strong> Great job!`;
      } else {
        feedback.className = 'quiz-feedback show incorrect';
        feedback.innerHTML = `<strong>✗ Incorrect.</strong> The correct answer is: <em>${current.a}</em>`;
      }

      nextBtn.classList.add('show');
    });
  });

  document.getElementById('btn-quiz-next')?.addEventListener('click', () => {
    state.quizIndex++;
    renderQuizQuestion();
  });
}

// Study Guide / List Mode
function renderGuide() {
  const guideList = document.getElementById('guide-content');
  if (!guideList) return;

  const categoriesToShow = state.selectedCategory === 'all' 
    ? CATEGORIES 
    : [state.selectedCategory];

  let html = '';
  let countMatched = 0;

  categoriesToShow.forEach(cat => {
    let items = QUESTIONS.filter(q => q.category === cat);
    if (state.statusFilter === 'mastered') items = items.filter(q => state.mastered.has(q.id));
    if (state.statusFilter === 'unmastered') items = items.filter(q => !state.mastered.has(q.id));
    if (state.statusFilter === 'starred') items = items.filter(q => state.starred.has(q.id));
    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase();
      items = items.filter(item => item.q.toLowerCase().includes(q) || item.a.toLowerCase().includes(q));
    }

    if (items.length === 0) return;
    countMatched += items.length;

    html += `
      <div class="guide-category-section">
        <div class="guide-cat-header">
          <span>${cat}</span>
          <span style="font-size: 0.85rem; font-weight: 500; opacity: 0.8;">${items.length} questions</span>
        </div>
        <ul class="guide-list">
          ${items.map(item => `
            <li class="guide-item" data-id="${item.id}">
              <div class="guide-item-top">
                <span class="guide-q">${item.id}. ${item.q}</span>
                <button class="btn-toggle-answer" data-id="${item.id}">Reveal</button>
              </div>
              <div class="guide-a" id="guide-a-${item.id}">${item.a}</div>
            </li>
          `).join('')}
        </ul>
      </div>
    `;
  });

  if (countMatched === 0) {
    html = `
      <div class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>No questions found</h3>
        <p>Try clearing your search query or selecting a different filter.</p>
      </div>
    `;
  }

  guideList.innerHTML = html;

  // Toggle single answer
  guideList.querySelectorAll('.btn-toggle-answer').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const id = btn.getAttribute('data-id');
      const aEl = document.getElementById(`guide-a-${id}`);
      if (aEl) {
        const isHidden = aEl.classList.toggle('hidden-answer');
        btn.textContent = isHidden ? 'Reveal' : 'Hide';
      }
    });
  });
}

function toggleAllAnswers(show) {
  const answers = document.querySelectorAll('.guide-a');
  const btns = document.querySelectorAll('.btn-toggle-answer');
  answers.forEach(a => {
    if (show) {
      a.classList.remove('hidden-answer');
    } else {
      a.classList.add('hidden-answer');
    }
  });
  btns.forEach(b => {
    b.textContent = show ? 'Hide' : 'Reveal';
  });
}

// Event Listeners
function setupEventListeners() {
  // Theme Toggle
  document.getElementById('btn-theme')?.addEventListener('click', toggleTheme);

  // Reset Progress
  document.getElementById('btn-reset')?.addEventListener('click', () => {
    if (confirm('Are you sure you want to reset all your learning progress and stars?')) {
      state.mastered.clear();
      state.starred.clear();
      savePersistedData();
      applyFilters();
      updateStats();
      renderCurrentMode();
    }
  });

  // Mode Tabs
  document.querySelectorAll('.mode-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.mode = tab.getAttribute('data-mode');
      renderCurrentMode();
    });
  });

  // Category select
  document.getElementById('category-select')?.addEventListener('change', (e) => {
    state.selectedCategory = e.target.value;
    state.currentIndex = 0;
    applyFilters();
    renderCurrentMode();
  });

  // Search input
  document.getElementById('search-input')?.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    state.currentIndex = 0;
    applyFilters();
    renderCurrentMode();
  });

  // Filter pills
  document.querySelectorAll('.pill-btn').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.pill-btn').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.statusFilter = pill.getAttribute('data-filter');
      state.currentIndex = 0;
      applyFilters();
      renderCurrentMode();
    });
  });

  // Shuffle toggle
  const shuffleBtn = document.getElementById('btn-shuffle');
  if (shuffleBtn) {
    shuffleBtn.addEventListener('click', () => {
      state.isShuffled = !state.isShuffled;
      shuffleBtn.classList.toggle('active', state.isShuffled);
      shuffleBtn.style.background = state.isShuffled ? 'var(--carolina-blue)' : '';
      shuffleBtn.style.color = state.isShuffled ? '#FFFFFF' : '';
      state.currentIndex = 0;
      applyFilters();
      renderCurrentMode();
    });
  }

  // Flashcard Actions
  document.getElementById('flashcard')?.addEventListener('click', (e) => {
    // Avoid flipping when clicking tool buttons on the card
    if (e.target.closest('.tool-btn') || e.target.closest('button')) return;
    flipCard();
  });

  document.getElementById('btn-flip')?.addEventListener('click', flipCard);
  document.getElementById('btn-prev')?.addEventListener('click', prevCard);
  document.getElementById('btn-next')?.addEventListener('click', nextCard);
  document.getElementById('btn-again')?.addEventListener('click', () => markCard(false));
  document.getElementById('btn-mastered')?.addEventListener('click', () => markCard(true));
  document.getElementById('btn-star')?.addEventListener('click', toggleStarCurrent);
  document.getElementById('btn-speak')?.addEventListener('click', speakCurrent);

  // Guide Actions
  document.getElementById('btn-show-all')?.addEventListener('click', () => toggleAllAnswers(true));
  document.getElementById('btn-hide-all')?.addEventListener('click', () => toggleAllAnswers(false));
  document.getElementById('btn-print')?.addEventListener('click', () => window.print());

  // Keyboard navigation
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

    if (state.mode === 'flashcard') {
      if (e.code === 'Space' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        flipCard();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextCard();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevCard();
      } else if (e.key === '1') {
        markCard(false);
      } else if (e.key === '2') {
        markCard(true);
      } else if (e.key === 's' || e.key === 'S') {
        toggleStarCurrent();
      } else if (e.key === 'r' || e.key === 'R') {
        const sBtn = document.getElementById('btn-shuffle');
        if (sBtn) sBtn.click();
      }
    }
  });

  // Touch Swipe on Flashcard
  let touchStartX = 0;
  let touchEndX = 0;
  const cardEl = document.getElementById('flashcard');
  if (cardEl) {
    cardEl.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    cardEl.addEventListener('touchend', (e) => {
      touchEndX = e.changedTouches[0].screenX;
      handleSwipe();
    }, { passive: true });
  }

  function handleSwipe() {
    const threshold = 50;
    if (touchEndX < touchStartX - threshold) {
      // Swiped left -> next
      nextCard();
    } else if (touchEndX > touchStartX + threshold) {
      // Swiped right -> prev
      prevCard();
    }
  }
}

// Run on page ready
document.addEventListener('DOMContentLoaded', init);
