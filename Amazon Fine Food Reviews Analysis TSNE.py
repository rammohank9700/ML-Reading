
# coding: utf-8

# # Amazon Fine Food Reviews Analysis
# 
# 
# Data Source: https://www.kaggle.com/snap/amazon-fine-food-reviews <br>
# 
# EDA: https://nycdatascience.com/blog/student-works/amazon-fine-foods-visualization/
# 
# 
# The Amazon Fine Food Reviews dataset consists of reviews of fine foods from Amazon.<br>
# 
# Number of reviews: 568,454<br>
# Number of users: 256,059<br>
# Number of products: 74,258<br>
# Timespan: Oct 1999 - Oct 2012<br>
# Number of Attributes/Columns in data: 10 
# 
# Attribute Information:
# 
# 1. Id
# 2. ProductId - unique identifier for the product
# 3. UserId - unqiue identifier for the user
# 4. ProfileName
# 5. HelpfulnessNumerator - number of users who found the review helpful
# 6. HelpfulnessDenominator - number of users who indicated whether they found the review helpful or not
# 7. Score - rating between 1 and 5
# 8. Time - timestamp for the review
# 9. Summary - brief summary of the review
# 10. Text - text of the review
# 
# 
# #### Objective:
# Given a review, determine whether the review is positive (Rating of 4 or 5) or negative (rating of 1 or 2).
# 
# <br>
# [Q] How to determine if a review is positive or negative?<br>
# <br> 
# [Ans] We could use the Score/Rating. A rating of 4 or 5 could be cosnidered a positive review. A review of 1 or 2 could be considered negative. A review of 3 is nuetral and ignored. This is an approximate and proxy way of determining the polarity (positivity/negativity) of a review.
# 
# 
# 

# ## Loading the data
# 
# The dataset is available in two forms
# 1. .csv file
# 2. SQLite Database
# 
# In order to load the data, We have used the SQLITE dataset as it easier to query the data and visualise the data efficiently.
# <br> 
# 
# Here as we only want to get the global sentiment of the recommendations (positive or negative), we will purposefully ignore all Scores equal to 3. If the score id above 3, then the recommendation wil be set to "positive". Otherwise, it will be set to "negative".

# In[1]:


get_ipython().run_line_magic('matplotlib', 'inline')
import warnings
warnings.filterwarnings("ignore")



import sqlite3
import pandas as pd
import numpy as np
import nltk
import string
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import confusion_matrix
from sklearn import metrics
from sklearn.metrics import roc_curve, auc
from nltk.stem.porter import PorterStemmer

import re
# Tutorial about Python regular expressions: https://pymotw.com/2/re/
import string
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.stem.wordnet import WordNetLemmatizer

from gensim.models import Word2Vec
from gensim.models import KeyedVectors
import pickle

from tqdm import tqdm
import os


# # [1]. Reading Data

# In[2]:



# using the SQLite Table to read data.
con = sqlite3.connect('database.sqlite') 
#filtering only positive and negative reviews i.e. 
# not taking into consideration those reviews with Score=3
# SELECT * FROM Reviews WHERE Score != 3 LIMIT 500000, will give top 500000 data points
# you can change the number to any other number based on your computing power

# filtered_data = pd.read_sql_query(""" SELECT * FROM Reviews WHERE Score != 3 LIMIT 500000""", con) 
# for tsne assignment you can take 5k data points

filtered_data = pd.read_sql_query(""" SELECT * FROM Reviews WHERE Score != 3 Limit 30000""", con) 

# Give reviews with Score>3 a positive rating, and reviews with a score<3 a negative rating.
def partition(x):
    if x < 3:
        return 0
    return 1

#changing reviews with score less than 3 to be positive and vice-versa
actualScore = filtered_data['Score']
positiveNegative = actualScore.map(partition) 
filtered_data['Score'] = positiveNegative
print("Number of data points in our data", filtered_data.shape)
filtered_data.head(3)
filtered_data.shape[0]


# In[3]:


display = pd.read_sql_query("""
SELECT UserId, ProductId, ProfileName, Time, Score, Text, COUNT(*)
FROM Reviews
GROUP BY UserId
HAVING COUNT(*)>1
""", con)


# In[4]:


print(display.shape)
display.head()


# In[5]:


display[display['UserId']=='AZY10LLTJ71NX']


# In[7]:


display['COUNT(*)'].sum()


# #  Exploratory Data Analysis
# 
# ## [2] Data Cleaning: Deduplication
# 
# It is observed (as shown in the table below) that the reviews data had many duplicate entries. Hence it was necessary to remove duplicates in order to get unbiased results for the analysis of the data.  Following is an example:

# In[8]:


display= pd.read_sql_query("""
SELECT *
FROM Reviews
WHERE Score != 3 AND UserId="AR5J8UI46CURR"
ORDER BY ProductID
""", con)
display.head()


# As can be seen above the same user has multiple reviews of the with the same values for HelpfulnessNumerator, HelpfulnessDenominator, Score, Time, Summary and Text  and on doing analysis it was found that <br>
# <br> 
# ProductId=B000HDOPZG was Loacker Quadratini Vanilla Wafer Cookies, 8.82-Ounce Packages (Pack of 8)<br>
# <br> 
# ProductId=B000HDL1RQ was Loacker Quadratini Lemon Wafer Cookies, 8.82-Ounce Packages (Pack of 8) and so on<br>
# 
# It was inferred after analysis that reviews with same parameters other than ProductId belonged to the same product just having different flavour or quantity. Hence in order to reduce redundancy it was decided to eliminate the rows having same parameters.<br>
# 
# The method used for the same was that we first sort the data according to ProductId and then just keep the first similar product review and delelte the others. for eg. in the above just the review for ProductId=B000HDL1RQ remains. This method ensures that there is only one representative for each product and deduplication without sorting would lead to possibility of different representatives still existing for the same product.

# In[9]:


#Sorting data according to ProductId in ascending order
sorted_data=filtered_data.sort_values('ProductId', axis=0, ascending=True, inplace=False, kind='quicksort', na_position='last')


# In[10]:


#Deduplication of entries
final=sorted_data.drop_duplicates(subset={"UserId","ProfileName","Time","Text"}, keep='first', inplace=False)
final.shape


# In[11]:


#Checking to see how much % of data still remains
(final['Id'].size*1.0)/(filtered_data['Id'].size*1.0)*100


# <b>Observation:-</b> It was also seen that in two rows given below the value of HelpfulnessNumerator is greater than HelpfulnessDenominator which is not practically possible hence these two rows too are removed from calcualtions

# In[12]:


display= pd.read_sql_query("""
SELECT *
FROM Reviews
WHERE Score != 3 AND Id=44737 OR Id=64422
ORDER BY ProductID
""", con)

display.head()


# In[13]:


final=final[final.HelpfulnessNumerator<=final.HelpfulnessDenominator]


# In[14]:


#Before starting the next phase of preprocessing lets see the number of entries left
print(final.shape)

#How many positive and negative reviews are present in our dataset?
final['Score'].value_counts()


# # [3].  Text Preprocessing.
# 
# Now that we have finished deduplication our data requires some preprocessing before we go on further with analysis and making the prediction model.
# 
# Hence in the Preprocessing phase we do the following in the order below:-
# 
# 1. Begin by removing the html tags
# 2. Remove any punctuations or limited set of special characters like , or . or # etc.
# 3. Check if the word is made up of english letters and is not alpha-numeric
# 4. Check to see if the length of the word is greater than 2 (as it was researched that there is no adjective in 2-letters)
# 5. Convert the word to lowercase
# 6. Remove Stopwords
# 7. Finally Snowball Stemming the word (it was obsereved to be better than Porter Stemming)<br>
# 
# After which we collect the words used to describe positive and negative reviews

# In[15]:


# https://stackoverflow.com/a/47091490/4084039
import re

def decontracted(phrase):
    # specific
    phrase = re.sub(r"won't", "will not", phrase)
    phrase = re.sub(r"can\'t", "can not", phrase)

    # general
    phrase = re.sub(r"n\'t", " not", phrase)
    phrase = re.sub(r"\'re", " are", phrase)
    phrase = re.sub(r"\'s", " is", phrase)
    phrase = re.sub(r"\'d", " would", phrase)
    phrase = re.sub(r"\'ll", " will", phrase)
    phrase = re.sub(r"\'t", " not", phrase)
    phrase = re.sub(r"\'ve", " have", phrase)
    phrase = re.sub(r"\'m", " am", phrase)
    return phrase


# In[16]:


# https://gist.github.com/sebleier/554280
# we are removing the words from the stop words list: 'no', 'nor', 'not'
# <br /><br /> ==> after the above steps, we are getting "br br"
# we are including them into stop words list
# instead of <br /> if we have <br/> these tags would have revmoved in the 1st step

stopwords= set(['br', 'the', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've",            "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself',             'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their',            'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those',             'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does',             'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of',             'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',            'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further',            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',            'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very',             's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're',             've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn',            "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn',            "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't",             'won', "won't", 'wouldn', "wouldn't"])


# In[17]:


# Combining all the above stundents 
from tqdm import tqdm
from bs4 import BeautifulSoup

preprocessed_reviews = []
# tqdm is for printing the status bar
for sentance in tqdm(final['Text'].values):
    sentance = re.sub(r"http\S+", "", sentance)
    sentance = BeautifulSoup(sentance, 'lxml').get_text()
    sentance = decontracted(sentance)
    sentance = re.sub("\S*\d\S*", "", sentance).strip()
    sentance = re.sub('[^A-Za-z]+', ' ', sentance)
    # https://gist.github.com/sebleier/554280
    sentance = ' '.join(e.lower() for e in sentance.split() if e.lower() not in stopwords)
    preprocessed_reviews.append(sentance.strip())


# <h2><font color='red'>[3.2] Preprocess Summary</font></h2>

# In[18]:


## Similartly you can do preprocessing for review summary also.

from tqdm import tqdm
preprocessed_summary = []
# tqdm is for printing the status bar
for sentance in tqdm(final['Summary'].values):
    sentance = re.sub(r"http\S+", "", sentance)
    sentance = BeautifulSoup(sentance, 'lxml').get_text()
    sentance = decontracted(sentance)
    sentance = re.sub("\S*\d\S*", "", sentance).strip()
    sentance = re.sub('[^A-Za-z]+', ' ', sentance)
    # https://gist.github.com/sebleier/554280
    sentance = ' '.join(e.lower() for e in sentance.split() if e.lower() not in stopwords)
    preprocessed_summary.append(sentance.strip())


# In[19]:



final.shape


# # [4] Featurization

# ## [4.1] BAG OF WORDS

# In[20]:


#BoW

data_pos = final[final["Score"] == 1].sample(n = 1200)
data_neg = final[final["Score"] == 0].sample(n = 1200)
final_2400 = pd.concat([data_pos, data_neg])
final_2400.shape
# count_vect = CountVectorizer() #in scikit-learn
# count_vect.fit(preprocessed_reviews)
# print("some feature names ", count_vect.get_feature_names()[:10])
# print('='*50)

# final_counts = count_vect.transform(preprocessed_reviews)
# print("the type of count vectorizer ",type(final_counts))
# print("the shape of out text BOW vectorizer ",final_counts.get_shape())
# print("the number of unique words ", final_counts.get_shape()[1])


# ## [4.2] Bi-Grams and n-Grams.

# In[21]:


#bi-gram, tri-gram and n-gram

#removing stop words like "not" should be avoided before building n-grams
# count_vect = CountVectorizer(ngram_range=(1,2))
# please do read the CountVectorizer documentation http://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.CountVectorizer.html
# you can choose these numebrs min_df=10, max_features=5000, of your choice
count_vect = CountVectorizer(ngram_range=(1,2), min_df=10, max_features=2400)
final_bigram_counts = count_vect.fit_transform(preprocessed_reviews)
print("the type of count vectorizer ",type(final_bigram_counts))
print("the shape of out text BOW vectorizer ",final_bigram_counts.get_shape())
print("the number of unique words including both unigrams and bigrams ", final_bigram_counts.get_shape()[1])


# ## [4.3] TF-IDF

# In[94]:


# tf_idf_vect = TfidfVectorizer(ngram_range=(1,2), min_df=10)
# tf_idf_vect.fit(preprocessed_reviews)
# print("some sample features(unique words in the corpus)",tf_idf_vect.get_feature_names()[0:10])
# print('='*50)

# final_tf_idf = tf_idf_vect.transform(preprocessed_reviews)
# print("the type of count vectorizer ",type(final_tf_idf))
# print("the shape of out text TFIDF vectorizer ",final_tf_idf.get_shape())
# print("the number of unique words including both unigrams and bigrams ", final_tf_idf.get_shape()[1])

tf_idf_vect = TfidfVectorizer(ngram_range=(1,2))
final_tf_idf = tf_idf_vect.fit_transform(final_2400['Text'].values)


# ## [4.4] Word2Vec

# In[143]:


# Train your own Word2Vec model using your own text corpus
i=0
list_of_sentance=[]
for sentance in preprocessed_reviews_TFIDFW2V:
    list_of_sentance.append(sentance.split())


# In[144]:


# Using Google News Word2Vectors

# in this project we are using a pretrained model by google
# its 3.3G file, once you load this into your memory 
# it occupies ~9Gb, so please do this step only if you have >12G of ram
# we will provide a pickle file wich contains a dict , 
# and it contains all our courpus words as keys and  model[word] as values
# To use this code-snippet, download "GoogleNews-vectors-negative300.bin" 
# from https://drive.google.com/file/d/0B7XkCwpI5KDYNlNUTTlSS21pQmM/edit
# it's 1.9GB in size.


# http://kavita-ganesan.com/gensim-word2vec-tutorial-starter-code/#.W17SRFAzZPY
# you can comment this whole cell
# or change these varible according to your need

is_your_ram_gt_16g=False
want_to_use_google_w2v = False
want_to_train_w2v = True

if want_to_train_w2v:
    # min_count = 5 considers only words that occured atleast 5 times
    w2v_model=Word2Vec(list_of_sentance,min_count=5,size=50, workers=4)
    print(w2v_model.wv.most_similar('great'))
    print('='*50)
    print(w2v_model.wv.most_similar('worst'))
    
elif want_to_use_google_w2v and is_your_ram_gt_16g:
    if os.path.isfile('GoogleNews-vectors-negative300.bin'):
        w2v_model=KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)
        print(w2v_model.wv.most_similar('great'))
        print(w2v_model.wv.most_similar('worst'))
    else:
        print("you don't have gogole's word2vec file, keep want_to_train_w2v = True, to train your own w2v ")


# In[145]:


w2v_words = list(w2v_model.wv.vocab)
print("number of words that occured minimum 5 times ",len(w2v_words))
print("sample words ", w2v_words[0:50])


# ## [4.4.1] Converting text into vectors using wAvg W2V, TFIDF-W2V

# #### [4.4.1.1] Avg W2v

# In[146]:


# average Word2Vec
# compute average word2vec for each review.
sent_vectors = []; # the avg-w2v for each sentence/review is stored in this list
for sent in tqdm(list_of_sentance): # for each review/sentence
    sent_vec = np.zeros(50) # as word vectors are of zero length 50, you might need to change this to 300 if you use google's w2v
    cnt_words =0; # num of words with a valid vector in the sentence/review
    for word in sent: # for each word in a review/sentence
        if word in w2v_words:
            vec = w2v_model.wv[word]
            sent_vec += vec
            cnt_words += 1
    if cnt_words != 0:
        sent_vec /= cnt_words
    sent_vectors.append(sent_vec)
print(len(sent_vectors))
print(len(sent_vectors[0]))


# #### [4.4.1.2] TFIDF weighted W2v

# In[140]:



preprocessed_reviews_TFIDFW2V = preprocessed_reviews[: 4000]


# In[147]:


# S = ["abc def pqr", "def def def abc", "pqr pqr def"]
model = TfidfVectorizer()
model.fit(preprocessed_reviews_TFIDFW2V)
# # we are converting a dictionary with word as a key, and the idf as a value
dictionary = dict(zip(model.get_feature_names(), list(model.idf_)))


# In[148]:


# TF-IDF weighted Word2Vec
tfidf_feat = model.get_feature_names() # tfidf words/col-names
# final_tf_idf is the sparse matrix with row= sentence, col=word and cell_val = tfidf

tfidf_sent_vectors = []; # the tfidf-w2v for each sentence/review is stored in this list
row=0;
for sent in tqdm(list_of_sentance): # for each review/sentence 
    sent_vec = np.zeros(50) # as word vectors are of zero length
    weight_sum =0; # num of words with a valid vector in the sentence/review
    for word in sent: # for each word in a review/sentence
        if word in w2v_words and word in tfidf_feat:
            vec = w2v_model.wv[word]
#             tf_idf = tf_idf_matrix[row, tfidf_feat.index(word)]
            # to reduce the computation we are 
            # dictionary[word] = idf value of word in whole courpus
            # sent.count(word) = tf valeus of word in this review
            tf_idf = dictionary[word]*(sent.count(word)/len(sent))
            sent_vec += (vec * tf_idf)
            weight_sum += tf_idf
    if weight_sum != 0:
        sent_vec /= weight_sum
    tfidf_sent_vectors.append(sent_vec)
    row += 1


# In[114]:


len(tfidf_sent_vectors)


# # [5] Applying TSNE

# <ol> 
#     <li> you need to plot 4 tsne plots with each of these feature set
#         <ol>
#             <li>Review text, preprocessed one converted into vectors using (BOW)</li>
#             <li>Review text, preprocessed one converted into vectors using (TFIDF)</li>
#             <li>Review text, preprocessed one converted into vectors using (AVG W2v)</li>
#             <li>Review text, preprocessed one converted into vectors using (TFIDF W2v)</li>
#         </ol>
#     </li>
#     <li> <font color='blue'>Note 1: The TSNE accepts only dense matrices</font></li>
#     <li> <font color='blue'>Note 2: Consider only 5k to 6k data points </font></li>
# </ol>

# ## [5.1] Applying TNSE on Text BOW vectors

# In[21]:


score_2400 = final_2400["Score"]
score_2400.shape
final_2400.head()


# In[22]:


count_vect = CountVectorizer() #in scikit-learn
final_counts = count_vect.fit_transform(final_2400['Text'].values)


# In[23]:


type(final_counts)
final_counts.get_shape()


# In[24]:


count_vect = CountVectorizer(ngram_range=(1,2))
final_bigram_counts = count_vect.fit_transform(final_2400['Text'].values)
final_bigram_counts.get_shape()


# In[25]:



from sklearn.preprocessing import StandardScaler

std_data = StandardScaler(with_mean = False).fit_transform(final_bigram_counts)
std_data.shape


# In[26]:


type(std_data)


# In[27]:


std_data = std_data.todense()


# In[28]:


type(std_data)


# In[29]:


# please write all the code with proper documentation, and proper titles for each subsection
# when you plot any graph make sure you use 
    # a. Title, that describes your plot, this will be very helpful to the reader
    # b. Legends if needed
    # c. X-axis label
    # d. Y-axis label
 
import numpy as np
from sklearn.manifold import TSNE
from sklearn import datasets
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sn

#TSNE

model = TSNE(n_components=2, random_state=0, perplexity = 30, n_iter = 2400)

tsne_data = model.fit_transform(std_data)

# creating a new data frame which help us in ploting the result data
tsne_data = np.vstack((tsne_data.T, score_2400)).T
tsne_df = pd.DataFrame(data=tsne_data, columns=("dim1", "dim2", "score"))

# Ploting the result of tsne
sns.FacetGrid(tsne_df, hue="score", size=6).map(plt.scatter, 'dim1', 'dim2').add_legend()
plt.title("TSNE for Bag of Words")
plt.show()


# Obervations :
# 
# ->here i have taken 1200 postive and 1200 negative data points and then i am standardzing the data.
#     then appling TSNE for BOW.
# -> from the TSNE plots , all the positive and negative reviews are overlapped with each other

# ## [5.1] Applying TNSE on Text TFIDF vectors

# In[48]:


# please write all the code with proper documentation, and proper titles for each subsection
# when you plot any graph make sure you use 
    # a. Title, that describes your plot, this will be very helpful to the reader
    # b. Legends if needed
    # c. X-axis label
    # d. Y-axis label


# In[120]:


#TFIDF

tf_idf_vect = TfidfVectorizer(ngram_range=(1,2))
final_tf_idf = tf_idf_vect.fit_transform(final_2400['Text'].values)


# In[121]:


# Standardization 
from sklearn.preprocessing import StandardScaler
std = StandardScaler(with_mean = False)
std_data = std.fit_transform(final_tf_idf)


# In[122]:


std_data = std_data.todense()


# In[33]:


# tsne
from sklearn.manifold import TSNE
model = TSNE(n_components = 2, perplexity = 50)
tsne_data = model.fit_transform(std_data)

tsne_data = np.vstack((tsne_data.T, score_2400)).T
tsne_df = pd.DataFrame(data = tsne_data, columns = ("dim1", "dim2", "score"))
sns.FacetGrid(tsne_df, hue = "score", size = 6).map(plt.scatter, "dim1", "dim2").add_legend()
plt.title("TSNE for TF-IDF")
plt.show()


# In[82]:


features = tf_idf_vect.get_feature_names()
len(features)


# In[86]:


print(final_tf_idf[3,:].toarray()[0]) 


# In[87]:


# source: https://buhrmann.github.io/tfidf-analysis.html
def top_tfidf_feats(row, features, top_n=25):
    ''' Get top n tfidf values in row and return them with their corresponding feature names.'''
    topn_ids = np.argsort(row)[::-1][:top_n]
    top_feats = [(features[i], row[i]) for i in topn_ids]
    df = pd.DataFrame(top_feats)
    df.columns = ['feature', 'tfidf']
    return df

top_tfidf = top_tfidf_feats(final_tf_idf[1,:].toarray()[0],features,25)


# Observations :
# 
# This one also looks same as like BOW, i.e both postive and negative reviews are over lapped each other.

# ## [5.3] Applying TNSE on Text Avg W2V vectors

# In[ ]:


# please write all the code with proper documentation, and proper titles for each subsection
# when you plot any graph make sure you use 
    # a. Title, that describes your plot, this will be very helpful to the reader
    # b. Legends if needed
    # c. X-axis label
    # d. Y-axis label


# In[46]:


import pickle
def savetofile(obj,filename):
    pickle.dump(obj,open(filename+".p","wb"), protocol=4)
savetofile(sent_vectors,"avg_w2v_vec")


# In[48]:


#Loading the variable from file
def openfromfile(filename):
    temp = pickle.load(open(filename+".p","rb"))
    return temp
avg_vec = openfromfile("avg_w2v_vec")


# In[52]:


avg_vec = np.array(avg_vec)
avg_vec.shape[0]


# In[62]:


get_ipython().run_cell_magic('time', '', 'from sklearn.manifold import TSNE\nfrom time import time\nimport random\n\nn_samples = 2000\nsample_cols = random.sample(range(1, avg_vec.shape[0]), n_samples)\nsample_features = avg_vec[sample_cols]\n# sample_features = df\nsample_class = final[\'Score\'][sample_cols]\nsample_class = sample_class[:,np.newaxis]\nprint(sample_features.shape,sample_class.shape)\nmodel = TSNE(n_components=2,random_state=0,perplexity=30)\n\nembedded_data = model.fit_transform(sample_features)\n# print(embedded_data.shape,sample_class.shape)\nfinal_data = np.concatenate((embedded_data,sample_class),axis=1)\nprint(final_data.shape)\nnewdf = pd.DataFrame(data=final_data,columns=["Dim1","Dim2","Class"])')


# In[63]:


sns.FacetGrid(newdf,hue="Class",size=6).map(plt.scatter,"Dim1","Dim2").add_legend()
plt.show()


# Here to same as above like BOW and TFIDF , which are not well separated

# ## [5.4] Applying TNSE on Text TFIDF weighted W2V vectors

# In[ ]:


# please write all the code with proper documentation, and proper titles for each subsection
# when you plot any graph make sure you use 
    # a. Title, that describes your plot, this will be very helpful to the reader
    # b. Legends if needed
    # c. X-axis label
    # d. Y-axis label


# In[ ]:


len(tfidf_sent_vectors)


# In[150]:



data_pos1 = final[final["Score"] == 1].sample(n = 2000)
data_neg1 = final[final["Score"] == 0].sample(n = 2000)
final_4000 = pd.concat([data_pos1, data_neg1])
final_4000.shape


# In[151]:


score_4000 = final_4000["Score"]
score_4000.shape
final_4000.head()


# In[152]:


#tsne
from sklearn.manifold import TSNE
model = TSNE(n_components=2, random_state=0, perplexity = 50, n_iter = 5000)

tsne_data = model.fit_transform(tfidf_sent_vectors)

tsne_data = np.vstack((tsne_data.T, score_4000)).T
tsne_df = pd.DataFrame(data=tsne_data, columns=("dim1", "dim2", "score"))

# Ploting the result of tsne
sns.FacetGrid(tsne_df, hue="score", size=6).map(plt.scatter, 'dim1', 'dim2').add_legend()
plt.title("TSNE for TF-IDF Word2vec")
plt.show()


# Here i have taken 4000 data points to see better plots and from the above plot we can see slightly some positive points are separated.

# # [6] Conclusions

# In[ ]:


# Write few sentance about the results that you got and observation that you did from the analysis
For BOW and TFIDF , i have 2400 points as the tnse plot is taking too long time.

From above all tsne plots ,negative and positive data points are over lapped with each other.
So as per the above plots we cannot make any assumptions which are not separable.
so we need to do other models to make some assumptions.
for TFIDF W2V , there is slightly plots which are showing that those are separated.

References:
    
    I have refered with some of Github  , kaggle sites and taken some code from provided .ipy notebooks in the course which is modified.

