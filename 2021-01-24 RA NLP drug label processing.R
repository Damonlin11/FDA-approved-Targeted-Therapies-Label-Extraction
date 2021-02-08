

library(XML)
library(RCurl)

url<-getURL("https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet") 
page<-htmlParse(url)

#Return the root node
root<-xmlRoot(page)
length(root)
names(root)

#Return the child nodes of the root node
child<-xmlChildren(root)

#Return the number of child nodes 
length(child)

#Return the names of child nodes
names(child)

grandchild<-xmlChildren(child[1]) 
length(grandchild)
names(grandchild)

## more functions
# the name of the node
xmlName(root)

# the number of child nodes
xmlSize(root)

# the names of the attributes of a node
xmlAttrs(root)

# the value of an attribute
xmlGetAttr(root, name = "itemtype")

# the text of a node, with recursion (get all the text), without recursion (only get the current node text)
xmlValue(root, recursive =  FALSE)
cat(xmlValue(root))

# use xpathSApply
titles<-xpathSApply(page, "//tbody/tr/td/a",xmlValue, recursive=FALSE)
filenames<-xpathSApply(page, "//tbody/tr/td/a",xmlGetAttr, name="href")

### extract FDA approaved targeted therapies (for single therapy) ###

library(XML)
library(RCurl)

# get the url and parse the link
url<-getURL("https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet") 
page<-htmlParse(url)

# get the link of FDA approaved targeted therapies
therapies <-xpathSApply(page, "//section[h2[@id = 'what-targeted-therapies-have-been-approved-for-specific-types-of-cancer']]//p//a", xmlGetAttr, name="href")
therapies

# test if the url is exist
link <- "https://www.cancer.gov/about-cancer/treatment/drugs/bevacizumab"
url.exists(link)

# get the targeted therapy url and parse it
ther_url<-getURL(link) 
ther_page<-htmlParse(ther_url)


# extract the therapy's name and brand name
ther_name <-xpathSApply(ther_page, "//article/div/h1", xmlValue)
ther_name

ther_br_name <-xpathSApply(ther_page, "//article//div[@class='two-columns brand-fda' and div[@class='column1']/text() = 'US Brand Name(s)']/div[@class='column2']")
ther_br_name

drug <- paste0(ther_name, " (", ther_br_name, ")")
drug

# extract the corresponding diseases (could be improved)
disease <-xpathSApply(ther_page, "//article//div[h2/text() = 'Use in Cancer']/ul/li/strong", xmlValue)
disease

# obtain DailyMed link
dailymed_link <-xpathSApply(ther_page, "//article//div/p/a[text() = 'FDA label information for this drug is available at DailyMed.']", xmlGetAttr, name="href")
dailymed_link

# if it is in multiple drug search page, select first drug link
drug_search <- 'https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query=CABOZANTINIB&pagesize=20&page=1&audience=consumer'
drug_search_url<-getURL(drug_search) 
drug_search_page<-htmlParse(drug_search_url)
dailymeddrug_link <-xpathSApply(drug_search_page, "(//div[@class = 'results-info'])[1]//a[@ class='drug-info-link']",  xmlGetAttr, name="href")
dailymeddrug_link

# extract the drug brand name from dailymed drug page
dailymeddrug_link <- paste0('https://dailymed.nlm.nih.gov', dailymeddrug_link)
dailymeddrug_url<-getURL(dailymeddrug_link) 
dailymeddrug_page<-htmlParse(dailymeddrug_url)
ther_br_name <- xpathSApply(dailymeddrug_page, "//span[@ id='drug-label']", xmlValue)
ther_br_name <- unlist(strsplit(ther_br_name, "-"))[1]
ther_br_name

drug <- paste0(ther_name, " (", ther_br_name, ")")
drug

# extract the gene/protein name
gene_protein <-xpathSApply(ther_page, "//article//div[h2/text() = 'Use in Cancer']/ul/li[strong/a/text() = 'Non-small cell lung cancer']//em[@class = 'gene-name']", xmlValue)
gene_protein

### a program to automatically extract drug names and diseases (for all therapies) ###

# get the url and parse the link
url<-getURL("https://www.cancer.gov/about-cancer/treatment/types/targeted-therapies/targeted-therapies-fact-sheet") 
page<-htmlParse(url)

# get the link of FDA approaved targeted therapies
therapies <-xpathSApply(page, "//section[h2[@id = 'what-targeted-therapies-have-been-approved-for-specific-types-of-cancer']]//p//a", xmlGetAttr, name="href")
therapies

drug_vec <- c()
web_gov <- 'https://www.cancer.gov'
drug_label <- c()
disease_label <- c()
dailymed_label <- c()

for (i in therapies) {
  link <- ""
  # make sure the url is unbroken
  if (grepl(web_gov, i)){
    link <- i
  }else {
    link <- paste0(web_gov, i)
  }
  
  # test if the url is exist
  # exist
  if (url.exists(link)) {
    ther_name <- ""
    ther_br_name <- ""
    
    # get the targeted therapy url and parse it
    #print(link)
    ther_url<-getURL(link) 
    ther_page<-htmlParse(ther_url)
    
    # extract the therapy's name and brand name
    ther_name <-xpathSApply(ther_page, "//article/div/h1", xmlValue)
    print(paste0(ther_name, '------'))
    
    if (length(ther_name)>0){
      # check the duplicate drug
      if (! ther_name %in% drug_vec) {
        drug_vec <- c(drug_vec, ther_name)
        
        # extract the therapy's brand name
        #ther_br_name <-xpathSApply(ther_page, "//article//div[@class='two-columns brand-fda' and div[@class='column1']/text() = 'US Brand Name(s)']/div[@class='column2']", xmlValue)
        
        # paste drug name and its brand name together
        #drug <- paste0(ther_name, " (", ther_br_name, ")")
        
        # obtain DailyMed link
        dailymed_link <-xpathSApply(ther_page, "//article//div/p/a[text() = 'FDA label information for this drug is available at DailyMed.']", xmlGetAttr, name="href")
        #print(dailymed_link)
        
        # extract the corresponding diseases
        disease <-xpathSApply(ther_page, "//article//div[h2/text() = 'Use in Cancer']/ul/li/strong", xmlValue)
        
        # make sure the dailymed url valid
        dailymeddrug_page <- NA
        if (url.exists(dailymed_link)) {
          
          # check if the link is directed to drug info page or multiple drug search page
          if (grepl('dailymed/drugInfo', dailymed_link)) {
            # drug info page and parse url
            dailymeddrug_url<-getURL(dailymed_link) 
            dailymeddrug_page<-htmlParse(dailymeddrug_url)
         
          }else if (grepl('dailymed/search', dailymed_link)) {
            
            # multiple drug search page, obtain the first drug link 
            drug_search_url<-getURL(dailymed_link) 
            drug_search_page<-htmlParse(drug_search_url)
            dailymeddrug_link <-xpathSApply(drug_search_page, "(//div[@class = 'results-info'])[1]//a[@ class='drug-info-link']",  xmlGetAttr, name="href")
            dailymeddrug_link <- paste0('https://dailymed.nlm.nih.gov', dailymeddrug_link)
            dailymeddrug_url<-getURL(dailymeddrug_link) 
            dailymeddrug_page<-htmlParse(dailymeddrug_url)
            
          }

        }
        
        if (!is.na(dailymeddrug_page)){
          
          # extract the brand name
          ther_br_name <- xpathSApply(dailymeddrug_page, "//span[@ id='drug-label']", xmlValue)
          ther_br_name <- unlist(strsplit(ther_br_name, "-"))[1]
          drug <- paste0(ther_name, " (", ther_br_name, ")")
          
          # work on diseases
          for (y in disease){
            
            #print(y)
            drug_label <- c(drug_label, drug)
            disease_label <- c(disease_label, y)
            dailymed_label <- c(dailymed_label, dailymeddrug_link)
          }
        }
      }
    }else { }
  }
}

drug_label
unique(drug_label)
disease_label
unique(disease_label)
dailymed_label

drug_disease <- data.frame(drug_label, disease_label, dailymed_label)
