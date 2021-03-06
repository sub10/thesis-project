import os
import requests
import json
import xmltodict

class APIAdapter:
	@staticmethod
	def get_search_results(query, retmax):
		baseurl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
		baseurl += "esearch.fcgi?db=pubmed&retmax=" + str(retmax) + "&term="

		data = requests.get(baseurl + query)
		parsed = xmltodict.parse(data.text)

		search_results = []
		for pmid in parsed['eSearchResult']['IdList']['Id']:
			search_results.append(int(pmid))

		return search_results


	@staticmethod
	def get_abstracts_foldername(query):
		return "abstracts/" + query

	@staticmethod
	def get_data_foldername(query):
		return "data/" + query

	@staticmethod
	def download_abstracts(query, groupSize):
		# get ids of search results
		pmids = APIAdapter.get_search_results(query, 10000)

		baseurl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
		baseurl += "db=pubmed&rettype=abstract&retmode=text&id="

		slist = []
		count = 0
		doccount = 1

		total_parts = len(pmids)/groupSize
		for cid in pmids:
			if count < groupSize:
				slist.append(cid)
				count+=1
				continue
			else:
				ids = ""
				for pmid in slist:
					ids += str(pmid) + ","
				print "Downloading part " + str(doccount) + " of " + str(total_parts)
				data = requests.get(baseurl+ids).text
				slist = []
				count = 0
				doccount+=1
				APIAdapter.split_abstracts(query, data.encode('utf8'))
		
		if count > 0:
			ids = ""
			for pmid in slist:
				ids += str(pmid) + ","
			data = requests.get(baseurl+ids).text
			APIAdapter.split_abstracts(query, data.encode('utf8'))


	@staticmethod
	def split_abstracts(query, data):
		if not os.path.exists(APIAdapter.get_abstracts_foldername(query)):
			os.mkdir(APIAdapter.get_abstracts_foldername(query))

		lines = data.split("\n")
		article = ""
		count = 0
		for line in lines:
			dummy = line[:-1]
			dummy = dummy.replace('[', ':')
			dummy = dummy.replace(']', ':')
			value = dummy.split(':')
			if(value[0] == "PMID"):
				pmid_value = value[1].replace(' ', '')
				wf = open(APIAdapter.get_abstracts_foldername(query) + "/" + pmid_value, 'w')
				article += line
				wf.write(article)
				wf.close()
				article = ""
				count += 1
			else:
				article += line

	@staticmethod
	def get_mesh_exp(query):
		baseurl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
		baseurl += "esearch.fcgi?db=pubmed&term="

		data = requests.get(baseurl + query)
		parsed = xmltodict.parse(data.text)

		return parsed['eSearchResult']['QueryTranslation']

	@staticmethod
	def extract_and_save(parsed, folder_name):
		for doc in parsed['collection']['document']:
			pmid = doc['id']
			annotations = []
			for passage in doc['passage']:
				if 'annotation' in passage:
					for annot in passage['annotation']:
						if type(annot) is not unicode:
							annotations.append(annot['infon'][1]['#text'])
			newobj = {}
			newobj['pmid'] = pmid
			newobj['annotations'] = annotations

			file = open(folder_name+pmid, 'w')
			json.dump(newobj, file)
			

	@staticmethod
	def run_gene_tagger(query):
		# use pubtator.py to populate the cache if this does not work.
		folder_name = 'genes_tagger/'+query+'/'
		os.mkdir(folder_name)

		pmids = set(line.strip() for line in open('cache/' + query))
		baseurl = "https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/Demo/RESTful/tmTool.cgi/Gene/"
		pmid_string = ""

		main_count = 0
		count = 0

		for pmid in pmids:
			pmid_string += pmid+","
			count = count+1
			if count == 20:
				request_url = baseurl + pmid_string + "/BioC/"
				data = requests.get(request_url)
				try:
					parsed = xmltodict.parse(data.text)
					APIAdapter.extract_and_save(parsed,folder_name)
				except:
					print "nothing"
				count = 0
				pmid_string = ""

		if pmid_string != "":
			request_url = baseurl + pmid_string + "/BioC/"
			data = requests.get(request_url)
			try:
				parsed = xmltodict.parse(data.text)
				APIAdapter.extract_and_save(parsed,folder_name)
			except:
				print "nothing"