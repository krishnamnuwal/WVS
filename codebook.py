"""Codebook: WVS-6 variable -> (section, sentence template, value labels).
Labels follow the WVS-6 master questionnaire; country-specific codes (religion,
state, language) were decoded by matching counts against the official
Results-by-Country PDF.  VERIFY against the official codebook before publication.
A template uses {v} for the label (or the number, for scales)."""

IMP = {1: "very important", 2: "rather important", 3: "not very important", 4: "not at all important"}
TRUST4 = {1: "trust them completely", 2: "trust them somewhat", 3: "do not trust them very much", 4: "do not trust them at all"}
LIKEME = {1: "very much like me", 2: "like me", 3: "somewhat like me", 4: "a little like me", 5: "not like me", 6: "not at all like me"}
FREQ5 = {1: "daily", 2: "weekly", 3: "monthly", 4: "less than monthly", 5: "never"}
OFTEN4 = {1: "often", 2: "sometimes", 3: "rarely", 4: "never"}
SCALE = None  # numeric scale, value inserted as-is

RELIGION = {60000000: "Hindu", 50000000: "Muslim", 70000000: "Buddhist", 80000000: "Christian",
            90000000: "of another religion", 100000020: "not a member of any religion"}
STATES_IN_CODE_ORDER = ["Andhra Pradesh", "Bihar", "Chhattisgarh", "Delhi", "Gujarat", "Haryana", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan",
    "Uttar Pradesh", "West Bengal", "Uttarakhand"]
STATE_COUNTS = [307, 332, 99, 94, 259, 122, 160, 239, 192, 256, 280, 355, 151, 278, 596, 294, 64]

CODEBOOK = [
 # --- who I am
 ("Who I am", "V240", "I am a {v}.", {1: "man", 2: "woman"}),
 ("Who I am", "V242", "I am {v} years old.", SCALE),
 ("Who I am", "V256", "I live in {v}.", "STATE"),
 ("Who I am", "V253", "The place I live in has {v} inhabitants.", {1: "under 2,000", 2: "2,000-5,000", 3: "5,000-10,000",
    4: "10,000-20,000", 5: "20,000-50,000", 6: "50,000-100,000", 7: "100,000-500,000", 8: "more than 500,000"}),
 ("Who I am", "V144", "I am {v}.", RELIGION),
 ("Who I am", "V57", "I am {v}.", {1: "married", 2: "living together with a partner as married", 3: "divorced",
    4: "separated", 5: "widowed", 6: "single"}),
 ("Who I am", "V58", "I have {v} children.", SCALE),
 ("Who I am", "V250", "I {v} with my parents.", {1: "live", 2: "do not live"}),
 ("Who I am", "V248", "My education: {v}.", {1: "no formal education", 2: "incomplete primary school", 3: "complete primary school",
    4: "incomplete secondary school (technical/vocational)", 5: "complete secondary school (technical/vocational)",
    6: "incomplete secondary school (university-preparatory)", 7: "complete secondary school (university-preparatory)",
    8: "some university, without a degree", 9: "a university degree"}),
 ("Who I am", "V255", "I {v}.", {1: "can read and write", 2: "cannot read and write"}),
 # --- work and money
 ("Work and money", "V229", "My work situation: {v}.", {1: "full-time employee", 2: "part-time employee", 3: "self-employed",
    4: "retired", 5: "housewife, not otherwise employed", 6: "student", 7: "unemployed", 8: "other"}),
 ("Work and money", "V235", "{v} the chief wage earner in my household.", {1: "I am", 2: "I am not"}),
 ("Work and money", "V238", "I would describe my family as {v}.", {1: "upper class", 2: "upper middle class", 3: "lower middle class",
    4: "working class", 5: "lower class"}),
 ("Work and money", "V239", "On a ladder of household incomes in India from 1 (lowest) to 10 (highest), my household is at {v}.", SCALE),
 ("Work and money", "V237", "In the past year my family {v}.", {1: "saved money", 2: "just got by", 3: "spent some savings",
    4: "spent savings and borrowed money"}),
 ("Work and money", "V59", "My satisfaction with my household's financial situation, from 1 (completely dissatisfied) to 10 (completely satisfied): {v}.", SCALE),
 ("Work and money", "V188", "In the last 12 months my family has {v} gone without enough food to eat.", OFTEN4),
 ("Work and money", "V191", "In the last 12 months my family has {v} gone without a cash income.", OFTEN4),
 # --- life
 ("My life", "V10", "Taking all things together, I am {v}.", {1: "very happy", 2: "rather happy", 3: "not very happy", 4: "not at all happy"}),
 ("My life", "V11", "My health these days is {v}.", {1: "very good", 2: "good", 3: "fair", 4: "poor"}),
 ("My life", "V23", "My satisfaction with my life as a whole, from 1 (completely dissatisfied) to 10 (completely satisfied): {v}.", SCALE),
 ("My life", "V55", "How much free choice and control I feel I have over my life, from 1 (none at all) to 10 (a great deal): {v}.", SCALE),
 ("My life", "V170", "In my neighbourhood I feel {v}.", {1: "very secure", 2: "quite secure", 3: "not very secure", 4: "not at all secure"}),
 ("My life", "V4", "Family is {v} in my life.", IMP),
 ("My life", "V5", "Friends are {v} in my life.", IMP),
 ("My life", "V8", "Work is {v} in my life.", IMP),
 ("My life", "V7", "Politics is {v} in my life.", IMP),
 ("My life", "V9", "Religion is {v} in my life.", IMP),
 # --- religion
 ("Religion", "V145", "Apart from weddings and funerals, I attend religious services {v}.", {1: "more than once a week", 2: "once a week",
    3: "once a month", 4: "only on special holy days", 5: "once a year", 6: "less often than once a year", 7: "never, practically never"}),
 ("Religion", "V152", "How important God is in my life, from 1 (not at all important) to 10 (very important): {v}.", SCALE),
 # --- other people
 ("How I see other people", "V24", "Generally speaking, I would say that {v}.", {1: "most people can be trusted",
    2: "you need to be very careful in dealing with people"}),
 ("How I see other people", "V56", "Whether most people would try to take advantage of me if they got the chance (1) or would try to be fair (10): {v}.", SCALE),
 ("How I see other people", "V102", "My family: I {v}.", TRUST4),
 ("How I see other people", "V103", "People in my neighbourhood: I {v}.", TRUST4),
 ("How I see other people", "V104", "People I know personally: I {v}.", TRUST4),
 ("How I see other people", "V105", "People I meet for the first time: I {v}.", TRUST4),
 ("How I see other people", "V106", "People of another religion: I {v}.", TRUST4),
 ("How I see other people", "V107", "People of another nationality: I {v}.", TRUST4),
 # --- what kind of person
 ("What kind of person I am", "V70", "Thinking up new ideas and being creative, doing things my own way: {v}.", LIKEME),
 ("What kind of person I am", "V71", "Being rich, having a lot of money and expensive things: {v}.", LIKEME),
 ("What kind of person I am", "V72", "Living in secure surroundings, avoiding anything that might be dangerous: {v}.", LIKEME),
 ("What kind of person I am", "V76", "Adventure and taking risks, having an exciting life: {v}.", LIKEME),
 ("What kind of person I am", "V77", "Always behaving properly, avoiding anything people would say is wrong: {v}.", LIKEME),
 ("What kind of person I am", "V79", "Tradition, following the customs handed down by my religion or family: {v}.", LIKEME),
 # --- views
 ("My views", "V84", "I am {v} in politics.", {1: "very interested", 2: "somewhat interested", 3: "not very interested", 4: "not at all interested"}),
 ("My views", "V96", "From 1 (incomes should be made more equal) to 10 (we need larger income differences as incentives for individual effort), my view is {v}.", SCALE),
 ("My views", "V99", "From 1 (competition is good) to 10 (competition is harmful), my view is {v}.", SCALE),
 ("My views", "V100", "From 1 (in the long run, hard work usually brings a better life) to 10 (hard work does not generally bring success, it is more a matter of luck and connections), my view is {v}.", SCALE),
 ("My views", "V201", "Cheating on taxes if you have a chance, from 1 (never justifiable) to 10 (always justifiable): {v}.", SCALE),
 ("My views", "V202", "Someone accepting a bribe in the course of their duties, from 1 (never justifiable) to 10 (always justifiable): {v}.", SCALE),
 ("My views", "V211", "I am {v} to be Indian.", {1: "very proud", 2: "quite proud", 3: "not very proud", 4: "not at all proud"}),
 # --- information
 ("How I get information", "V217", "How often I read a daily newspaper: {v}.", FREQ5),
 ("How I get information", "V219", "How often I watch TV news: {v}.", FREQ5),
 ("How I get information", "V223", "How often I use the internet: {v}.", FREQ5),
]
