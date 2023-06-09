#!/usr/bin/env python
# coding: utf-8


print("\n\nParameters\n")
import re, os, sys, subprocess
from pandas import DataFrame 
import pandas as pd
import requests
import numpy as np
from datetime import datetime
import urllib.request
import warnings
warnings.filterwarnings("ignore")



#####
##############
###################
########################


#### distribucion hipergeometrica
def lFactorial(val):
    returnValue = 0
    i = 2
    while i <= val:
        returnValue = returnValue + np.log(i)
        i += 1
    return returnValue
def lNchooseK(n, k):
    answer = 0
    if k > (n-k):
        k = n-k
    i = n
    while i > (n - k):
        answer = answer + np.log(i)
        i -= 1
    answer = answer - lFactorial(k)
    return answer
def hypergeometric(n, p, k, r):
    
    """
    traducido de un lenguaje de perl (GeneMerge) a lenguaje de Python 
    #https://doi.org/10.1093/bioinformatics/btg114
    n = total poblacion
    p = parte de la poblacion con un item especifico
    k = total de la muestra
    r = parte de la muestra con el mismo item que p
    n, p, k, r = 6157, 222, 473, 81
    hypergeometric(n, p, k, r) = 5.3138310345009354e-36
    """
    nnp = p
    nq = n - p
    p = p/n
    log_n_choose_k = lNchooseK(n, k)
    
    top = k
    if nnp < k:
        top = nnp
    lfoo = lNchooseK(nnp, top) + lNchooseK(n*(1-p), k-top)
    suma = 0
    i = top
    while i >= r:
        suma = suma + np.exp(lfoo - log_n_choose_k)
        if i > r:
            lfoo = lfoo + np.log(i / (nnp-i+1)) +  np.log((nq - k + i) / (k-i+1))
        i -= 1
    if suma > 1:
        suma = 1
    return suma




#####
##############
###################
########################


def enrichment_analysis(BACK = DataFrame([]), LIST = DataFrame([]), ASSO = DataFrame([]), DESC = DataFrame([]), FDR = 0):
    # Total of proteins with terms in list (for hypergeometric dustribution)
    total_protein_list = len(set(LIST.Entry.tolist()))
    #total_protein_list

    # Get all list terms involved in a category
    list_cat = LIST.merge(ASSO , on = 'Entry' , how = 'left').dropna().drop_duplicates()
    yyy = list_cat.merge(DESC , on = 'base', how='left').dropna().drop_duplicates()
    list_category = DataFrame(yyy.groupby('base').Entry.size()).reset_index()

    # Total of proteins with terms in background
    total_proteins_bg = len(set(BACK.Entry.tolist()))#.drop_duplicates().count()

    # Get all background terms involved in a category
    category = BACK.merge(ASSO , on = 'Entry', how = 'left').reset_index(drop=True).dropna()
    xxx = category.merge(DESC , on = 'base', how = 'left').dropna().drop_duplicates()
    cat = DataFrame(xxx.groupby('base').Entry.count()).reset_index()

    #######################################################################
    #########################  Statistical test   #########################
    #######################################################################
    ## list_count = proteins in list
    ## back_count = proteins in background by category (P or F or C or kegg)
    statistics = list_category.merge(cat, on = 'base', how = 'left')
    statistics.columns = ['base','list_count', 'back_count']



    ## following the GeneMerge1.4 approach we use non-singletons as multiple testing value
    multiple_testing_value = statistics[statistics.back_count > 1].count()[0]

    #print(multiple_testing_value)
    statistics['tot_list']=total_protein_list
    statistics['tot_back']=total_proteins_bg

    ## Hypergeometric Distribution
    #hypergeom.sf(k, M, n, N, loc=0)
    # k = number of genes/proteins associated to the process "cell cycle"
    # M = total number of genes/proteins with some annotation
    # n = total number of genes/proteins annotated for "cell cycle" inside M
    # N = number of genes associated to at least one Biological Process in the Gene Ontology.
    # https://docs.scipy.org/doc/scipy-0.19.1/reference/generated/scipy.stats.hypergeom.html
    # example =  hypergeom.sf(8-1, total_proteins_bg, 199, total_protein_list, loc=0)

    ## Loop for calculate hypergeometric distribution
    p_val=[]
    for index, row in statistics.iterrows():
        b = hypergeometric(total_proteins_bg, row['back_count'], total_protein_list, row['list_count'])
        p_val.append(b)
    statistics['P'] = p_val


    ## Loop for calculate Bonferroni correction
    Bonf_cor=[]
    for x in statistics.P:
        Bonf_cor.append(x*multiple_testing_value)
    statistics['Bonf_corr'] = Bonf_cor


    ## Loop for calculate FDR, sorting P-value before this test
    statistics = statistics[statistics.list_count > 1].reset_index(drop=True)

    statistics = statistics.sort_values(by ='P',ascending=True).reset_index(drop=True)

    statistics['Rank'] = statistics.index + 1

    #
    FDR_val=[]
    for x in statistics.Rank:
        FDR_val.append((x/statistics.count()[0])*FDR)
    statistics['FDR'] = FDR_val

    ## Loop to add boolean value to statistically significant
    # T = True if P < FDR
    # F = False if P > FDR

    significant = []
    for index, row in statistics.iterrows():
        if row.P <= row.FDR:
            significant.append('T')
        if row.P > row.FDR:
            significant.append('F')
    statistics['Sig'] = significant

    statistics = statistics.merge(DESC, on = 'base', how = 'left')

    ff = []
    for i in statistics.base.drop_duplicates():
        df = list_cat[list_cat.base == i]
        ff.append([i, ';'.join(df.Entry.tolist())])
    enrichment = DataFrame(ff, columns = ['base','entry'])

    statistics = statistics.merge(enrichment, on = 'base', how = 'left')
    return statistics

#####
##############
###################
########################







def del_stop_process():
    if os.path.exists("short_GO.py"): os.remove("short_GO.py")
    sys.exit()


parametros = open('NeVOmics_params.txt', 'r')
parametros = parametros.read()
#print(parametros)


# ## definimos los parametros para  GO

# # <font color=red>incluir seleccion de UniProtKB Annotation of UniProtGOA Annotation<font>


#######################
# parametros elegidos
method_P = 'FDR' # default

# definimos la localizacion y nombre del archivo elegido
file_path = re.search('filelocation.*', parametros).group().split('=')[1]

# colores elegidos por el usuario para los terminos y edges
usercolormap = re.search('edgecolor.*', parametros).group().split('=')[1]

# coloes para rampa, asignacion a valores, numericos relacionados a los genes o proteinas
colormap_definido = re.search('networkcolor.*', parametros).group().split('=')[1]

# titulo para la barra de colormap
barcolortitle = re.search('usertext.*', parametros).group().split('=')[1]

# definicion de nodos si no hay valores asociados a los nodos de la red, default blue
nodecolorsinback = re.search('uniquecolor.*', parametros).group().split('=')[1]

# Biological process
bpfdr = float(re.search('bpfdr.*', parametros).group().split('=')[1])  / 100
bpplots = re.search('bpplots.*', parametros).group().split('=')[1]

# Molucular Function
mffdr = float(re.search('mffdr.*', parametros).group().split('=')[1])  / 100
mfplots = re.search('mfplots.*', parametros).group().split('=')[1]

# Cellular Component
ccfdr = float(re.search('ccfdr.*', parametros).group().split('=')[1])  / 100
ccplots = re.search('ccplots.*', parametros).group().split('=')[1]

# crear redes? 0 es no, 1 es si
createnetworks = re.search('networksplots.*', parametros).group().split('=')[1]

# crear circos? 0 es no, 1 es si
createcircos = re.search('circosplots.*', parametros).group().split('=')[1]

# etiqueta de nodos ['Gene', 'UniProt']
labelnode = re.search('labelnode.*', parametros).group().split('=')[1]

print('method_P =', method_P)
#print('file_path =', file_path)
print('usercolormap =', usercolormap)
print('colormap_definido =', colormap_definido)
print('barcolortitle =', barcolortitle)
print('nodecolorsinback =', nodecolorsinback)
# Biological process
print('bpfdr =', bpfdr)
print('bpplots =', bpplots)
# Molucular Function
print('mffdr =', mffdr)
print('mfplots =', mfplots)
# Cellular Component
print('ccfdr =', ccfdr)
print('ccplots =', ccplots)

print('createnetworks =', createnetworks)
print('createcircos =', createcircos)
print('labelnode =', labelnode)

anotacion_goa = re.search('anotacion_goa.*', parametros).group().split('=')[1]
print('#\nanotacion_goa = ', anotacion_goa)

##################
anotacion_uniprot = '1' # default
###################



## read file
inp_file=pd.read_csv(file_path,sep='\t',header=None)   
    
## explore input file
if len(inp_file.columns) == 1:
    hayvalores = 'nohayvalores'
    inp_file['values'] = 1
    ## only gene list
    list_input=inp_file.rename(columns={0:'Entry'},index=str) 
if len(inp_file.columns) == 2:
    hayvalores = 'sihay'
    ## gene list and vales
    list_input=inp_file.rename(columns={0:'Entry',1:'values'},index=str) ## gene list and values
if len(inp_file.columns) == 3:
    hayvalores = 'sihay'
    ## gene list, values and background
    list_input=inp_file.rename(columns={0:'Entry',1:'values',2:'Background'},index=str)




## exttract id-organism
#id_organism = requests.get("https://www.uniprot.org/uniprot/?query="+list_input.Entry[0]+"&sort=score&columns=organism-id&format=tab&limit=1").content.decode()
#Prefix = id_organism.split('\n')[1]


#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-

## exttract id-organism

inpfile = []
with open(file_path) as fq:
    for e, i in enumerate(fq):
        i = i.rstrip()
        inpfile.append(i.split('\t'))
e1 = [i[0] for e, i in enumerate(inpfile) if e == 0][0]

id_organism = requests.get("https://rest.uniprot.org/uniprotkb/"+e1+".txt").content.decode().split('\n')

taxid = [i for i in id_organism if 'OX   ' in i]
if taxid == []:
    pass
else:
    Prefix = re.sub('=', '', re.findall('=\d+', [i for i in id_organism if 'OX   ' in i][0])[0])


#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-

if id_organism == '':
    print('Organism not found')
    #del_stop_process()
else:
    pass





## Create a folder
os.makedirs('data',exist_ok=True)




# save all ontology from go-basic.obo file from GOC

import os, fnmatch
def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

gobasic = open('../NeVOmics_img/go-basic.obo', 'r')
for line in gobasic:
    if re.search('data-version: .*', line):
        pat = re.search('data-version: .*', line).group()
        go_version = re.sub('data-version: releases.', '', pat)
        print('\nOntology version: ', go_version)
        print('Downloaded from: http://geneontology.org/docs/download-ontology/', '\n')
        break
        
with open('../NeVOmics_img/go-basic.obo', 'r') as g:
    go_obo = g.read()
g.close()
ontology_file = go_obo.split('[Term]')

aspect = {'biological_process':'P', 'molecular_function':'F', 'cellular_component':'C'}
items = []
for i in ontology_file[1:len(ontology_file)]:
    items.append([i.split('\n')[1].split(': ')[1],
                 i.split('\n')[2].split(': ')[1],
                 aspect[i.split('\n')[3].split(': ')[1]]])
ontologia = DataFrame(items, columns = ['GO', 'Term', 'Aspect'])


ontologia[ontologia['Aspect'].str.contains('P') == True][['GO','Term']].to_csv('data/GO_BP.txt', sep = '\t', index = None)
ontologia[ontologia['Aspect'].str.contains('F') == True][['GO','Term']].to_csv('data/GO_MF.txt', sep = '\t', index = None)
ontologia[ontologia['Aspect'].str.contains('C') == True][['GO','Term']].to_csv('data/GO_CC.txt', sep = '\t', index = None)


# ## ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# ##        UniProtKB
# ## ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


##############################################################
################           Uniprot         ###################
##############################################################

file_uniprot = find('annotation_'+Prefix, '../')
if file_uniprot == ('' or []):
    uni = urllib.request.urlretrieve('https://www.uniprot.org/uniprot/?query=organism:'+Prefix+'&format=tab&columns=id,genes,go-id', 'annotation_'+Prefix)
    prot_version = uni[1]['Last-Modified']
    go_uniptot_version = uni[1]['Last-Modified']
    print('UniProtKB version: ', prot_version)
    print('Entries: ', uni[1]['X-Total-Results'])
    with open(uni[0], 'a') as fq:
        fq.write('#'+prot_version)
        fq.close()
    
    acc_GOid=pd.read_csv('annotation_'+Prefix,sep='\t')#.dropna().reset_index(drop=True)
    acc_GOid.columns = ['Entry', 'Gene', 'GO']
else:
    file_uniprot = re.sub('\\\\', '/', file_uniprot[0])
    print('It already exists:', file_uniprot)
    acc_GOid=pd.read_csv(file_uniprot,sep='\t')#.dropna().reset_index(drop=True)
    acc_GOid.columns = ['Entry', 'Gene', 'GO']
    go_uniptot_version = re.sub('#', '', acc_GOid.Entry.tolist()[-1])
    print('UniProtKB version: ', re.sub('#', '', acc_GOid.Entry.tolist()[-1]))
    acc_GOid = acc_GOid[acc_GOid.Entry.str.contains('#') == False]
    print('Entries: ', acc_GOid.Entry.count())


# ## exploracion de la anotacion de Uniprot


# es un df con Entries sin anotación GO en Uniprot
con_nas = acc_GOid[pd.isna(acc_GOid['GO'])]


# es un df con Entries que tienen anotacion en Uniprot, pero algunos genes no tienen identificador
sin_nas = acc_GOid[pd.notna(acc_GOid['GO'])]
# del df anterior extraigo un df de genes que no tienen nombre, en otra celda edito estos genes
genes_sin_name = sin_nas[pd.isna(sin_nas['Gene'])]
sin_nas = sin_nas[pd.notna(sin_nas['Gene'])]


# asigno el Entry como nombre del gen
new_gene_name = []
for i, j in genes_sin_name.iterrows():
    new_gene_name.append([j.Entry, 'Entry:'+j.Entry, j.GO])


df_new_gene_name = DataFrame(new_gene_name, columns = ['Entry', 'Gene', 'GO'])


Entry_GOid = pd.concat([sin_nas, df_new_gene_name]).drop_duplicates()


uniprot_anotation_org = []
for index, row in Entry_GOid.iterrows():
    for j in row.GO.split('; '):
        if re.search('GO:\d+', j):
            uniprot_anotation_org.append([row.Entry, row.Gene, re.search('GO:\d+', j).group()])
# este df contiene toda la anotación GO en uniprot del organismo en estudio
Entry_GOid_annotated =DataFrame(uniprot_anotation_org, columns = ['Entry', 'Gene', 'GO'])


# ## df con toda la informacion funcional GOA capturada usando los ids de uniprot


uniprot_entry_go_term = Entry_GOid_annotated.merge(ontologia, on = 'GO', how = 'left').dropna()
uniprot_entry_go_term['Gene'] = [i.split(' ')[0] for i in uniprot_entry_go_term.Gene.tolist()]
uniprot_entry_go_term = uniprot_entry_go_term[['Entry', 'GO', 'Term', 'Aspect', 'Gene']]
uniprot_entry_go_term


total = len(uniprot_entry_go_term.Entry.drop_duplicates().tolist())
print('\nUniProt Entries with GO Terms:', total)

# ## ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# ##        Uniprot GOA
# ## ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


def hojas(dict_hoja = dict()):
    final = []
    for i in dict_hoja.keys():
        for j in dict_hoja[i]['results']:
            final.append([re.sub('UniProtKB:','', j['geneProductId']),
                           j['qualifier'],
                           j['goId'],
                           j['goName'],
                           j['goEvidence'],
                           j['goAspect'],
                           j['evidenceCode'],
                           j['reference'],
                           j['withFrom'],
                           j['taxonId'],
                           j['taxonName'],
                           j['assignedBy'],
                           j['extensions'],
                           j['targetSets'],
                           j['symbol'],
                           j['date'],
                           j['synonyms'],
                           j['name']])
    return final


if anotacion_goa == '1':

    file_goa = ''.join(find('Complete_Annotation_'+Prefix+'_goa', '../'))
    file_goa1 = re.sub('\\\\', '/', file_goa)
    file_goa2 = file_goa1.split('/')[-1]
    
    if file_goa2 == '':
        from bioservices import QuickGO
        qg = QuickGO()
        info_goa = requests.get('https://www.ebi.ac.uk/QuickGO/services/annotation/downloadSearch?geneProductId='+Entry_GOid_annotated.Entry.drop_duplicates().tolist()[0])
        goa_information = info_goa.headers['Date']
        print('GOA annotation:', goa_information)
        print('The full annotation will be downloaded, this may take some time, from 10 min to 2 h')
        # descarga de la anotacion completa
        ##############################################################
        ################       Uniprot GOA         ###################
        ##############################################################
        ## GOA Proteome Sets
        # descarga anotacion completa GOA usando bioservices module
        # los arhcivos .gaf están incompletos y no muestran la anotación completa, por eso se usa bioservices
        #

        from datetime import datetime

        print('\nTotal UniProt entries expected:', total)
        print('Mapping: (UniprotKB Entries | Found Entries | Missing Entries)')
        inicio = datetime.now()
        dl = 0
        resultado = []
        suma = 0
        for k in range(0, total,100):
            tim = datetime.now() - inicio
            serie_cien = ''.join(','.join(Entry_GOid_annotated.Entry.drop_duplicates().tolist()[k:k+100]))
            ##
            exploracion = qg.Annotation(page = 1, geneProductId  = serie_cien)
            total_pages = exploracion['pageInfo']['total']
            lista_paginas = list(range(1,total_pages+1))
            res = {}
            ids = []
            for i in list(range(1,total_pages+1)):
                res[i] = qg.Annotation(page = i, geneProductId  = serie_cien)
                if res[i] == 400:
                    res.pop(i)
                for f in res[i]['results']:
                    ids.append(re.sub('-.*', '',f['geneProductId'].split(':')[1]))
            suma += len(set(ids))
            ##
            dl += len(serie_cien.split(','))
            done = int(40 * dl / total)
            sys.stdout.write("\r"+'{}'.format(tim).split('.')[0]+" [%s%s] (%s | %s | %s)" % ('>' * done, ' ' * (40-done),
                                                                                             dl, suma, (dl-suma)))
            sys.stdout.flush()

    
            header = ['Entry','qualifier','goId','goName','goEvidence','goAspect','evidenceCode','reference',
                        'withFrom','taxonId','taxonName','assignedBy','extensions','targetSets','symbol',
                        'date','synonyms','name']
            resultado.append(DataFrame(hojas(dict_hoja = res), columns = header))
    
        print('\n')
        complete_annotation = pd.concat(resultado)
        complete_annotation.to_csv('Complete_Annotation_'+Prefix+'_goa', sep = '\t',index=None)
        with open('Complete_Annotation_'+Prefix+'_goa', 'a') as fq:
            fq.write('#'+goa_information)
            fq.close()
    else:
        print('\nIt already exists:', file_goa1)
        complete_annotation = pd.read_csv(file_goa1, sep='\t')
        goa_information = re.sub('#', '', complete_annotation.Entry.tolist()[-1])
        print('GOA annotation:', goa_information)
        complete_annotation = complete_annotation[complete_annotation.Entry.str.contains('#') == False]
        
    ### recuperacion de Entries no encontrados en Quickgo, se obtienen a partir de uniprot   
    # removemos Entries que tienen guiones
    complete_annotation = complete_annotation[complete_annotation['Entry'].str.contains('-') == False]
    goa_annotation = complete_annotation[['Entry', 'goId', 'symbol']]
    goa_annotation.columns = ['Entry', 'GO', 'Gene']
    goa_entry_go_term = goa_annotation.merge(ontologia, on = 'GO', how = 'left').dropna()
    # recuperadas no mapeadas = rnm
    rnm = uniprot_entry_go_term.merge(goa_entry_go_term, on = 'Entry', how = 'left')
    rnm = rnm[pd.isnull(rnm).any(axis=1)]
    rnm2 = rnm[['Entry']].drop_duplicates().merge(uniprot_entry_go_term, on = 'Entry', how = 'left')
    ## df con toda la informacion funcional GOA capturada usando los ids de uniprot
    goa_entry_go_term = pd.concat([goa_entry_go_term, rnm2])
    total = len(goa_entry_go_term.Entry.drop_duplicates().tolist())
    print('\nGOA Entries:', total, '\n')  
    
    goa_entry_go_term[['Entry','GO']].drop_duplicates().to_csv('data/GOA_Association.txt',index=None,sep='\t')

else:
    pass

# ## Archivos para enriquecimiento




#############  funciones

# funcion para crear archivos para enriquecimiento, ingresar diferentes data frames
def enrichment_files(df = DataFrame([])):
    if len(inp_file.columns) == 3:
        print('With background')
        provicional = list_input[['Background']].rename(columns={'Background':'Entry'})
        background_info = provicional.merge(df, on = 'Entry', how = 'inner')
    
        # guardar archivo background, con la columna de genes
        background_info[['Entry']].drop_duplicates().to_csv('data/Background.txt',index=None)
        print('data/Background.txt')

        # 2.- Preparation of list with pathways
        ## Protein list mapping against "background_info" and then save this list
        list_input_match = list_input[['Entry']].merge(background_info,how="left", on='Entry').dropna().drop_duplicates()
        list_input_match[['Entry']].drop_duplicates().to_csv('data/List.txt',index=None)
        print('data/List.txt')
    
        # 3.- background with: Entry	GO, for association file
        background_info[['Entry','GO']].to_csv('data/UniProt_Association.txt',index=None,sep='\t')
        print('data/Association.txt')
        
    else:
        print('No background')
        background_info = uniprot_entry_go_term
        
        # guardar archivo background, con la columna de genes
        background_info[['Entry']].drop_duplicates().to_csv('data/Background.txt',index=None)
        print('data/Background.txt')
    
        # 2.- Preparation of list with pathways
        ## Protein list mapping against "background_info" and then save this list
        list_input_match = list_input[['Entry']].merge(background_info,how="left", on='Entry').dropna().drop_duplicates()
        list_input_match[['Entry']].drop_duplicates().to_csv('data/List.txt',index=None)
        print('data/List.txt')
    
        # 3.- background with: Entry	GO, for association file
        background_info[['Entry','GO']].to_csv('data/UniProt_Association.txt',index=None,sep='\t')
        print('data/Association.txt')
        
                
    ######
    no_anotadas = []
    for i in list_input.Entry.drop_duplicates().dropna().tolist():
        if i in list_input_match.Entry.drop_duplicates().tolist():
            continue
        else:
            no_anotadas.append(i)
    return list_input_match, no_anotadas
    





# funcion para explorar si hay terminos enriquecidos, si hay crea un df,
# si no hay crea los archivos excel y termina el proceso
from tkinter import messagebox
def filtro_significancia(df = DataFrame([]), info = '', asso_file = '', fdr_val = 0, no_annot = [], db = ''):
    if df[df.Sig == 'T']['FDR'].count() >= 1: # al menos un valor de FDR es significativo      
        results_sig = df[df.Sig == 'T']
        vertice = [(k, j) for i, k in zip(results_sig.entry.tolist(), results_sig.base.tolist()) for j in i.split(';')]
        proteins_count = len(set([i[1] for i in vertice]))
        GO_count = results_sig.base.count()
        
        return results_sig 
        
    else:
        # si no hay GO terms enriquecidos se generan los archivos excel sin los edges
        if len(df) < 1:
            input_background = 0
            go_background = 0
            go_lista = 0
            singletons_value = 0
        else:
            input_background = int(float(df.tot_back.iloc[0:1]))
            go_background = df.tot_back.iloc[0]
            go_lista = df.tot_list.iloc[0]
            singletons_value = int(float(df.Bonf_corr.iloc[-1:]) / float(df.P.iloc[-1:]))
        
        results_sig = df[df.Sig == 'T']
        reporte = {'base':[np.nan,
                           'GO DB Last-Modified',
                           'Input file name',
                           'Association file name',
                           'Total number of background',
                           'Total number of list',
                           'Background with GO Terms',
                           'List input with GO Terms',
                           'Non-singletons value for Bonf_corr',
                           'Correction Method',
                           'Value',
                           np.nan,
                           'Proteins with no information in UniProtKB',
                           ';'.join(no_annot)],
                'list_count':[np.nan,
                              info,
                              file_path,
                              asso_file,
                              input_background,
                              list_input['Entry'].drop_duplicates().count(),
                              go_background,
                              go_lista,
                              singletons_value,
                              'FDR',
                              str(fdr_val)+' ('+str(np.round(fdr_val * 100,1))+'%)',
                              np.nan,
                              len(no_annot),
                              np.nan]}
        information = DataFrame(reporte)
        informe_final = pd.concat([results_sig, information], axis=0, sort=False).rename(columns={'base':'GO'})
    
        informe_final = informe_final[['GO', 'list_count', 'back_count', 'tot_list', 'tot_back', 'P', 'Bonf_corr',
           'Rank', 'FDR', 'Sig', 'Term', 'entry']]
        writer = pd.ExcelWriter(db+'_Enrichment_'+asso_file.split('.')[0]+'_FDR_'+str(fdr_val)+'.xlsx')

        informe_final.to_excel(writer,'Significant GO Terms',index=False)

        df.to_excel(writer,'Enrichment Results',index=False)
    
        writer.save()
        
        print('!!!!!!!!!!!!!!\nLess than 2 significant terms were identified in '+asso_file.split('.')[0]+' for the chosen FDR,'+              ' try another FDR.\nTo create networks it is necessary to obtain at least 2 terms.')

        #root = tk.Tk()
        #root.overrideredirect(1)
        #root.withdraw()
        #advertencia = messagebox.showinfo('Status', 'Finished Analysis\n\n'+\
        #                             '\nLess than 2 significant terms were identified in '+asso_file.split('.')[0]+' for the chosen FDR,'+\
        #                             ' try another FDR.\n'+\
        #                             'To create networks it is necessary to obtain at least 2 terms.')
        #root.destroy()
        return DataFrame([None])




def termino_corto(df = DataFrame([])):
    etiquetas = []
    for i in df.Term:
        i = i.rstrip()
        if len(i.split(' ')) == 1:
            etiquetas.append(i)
        if len(i.split(' ')) == 2:
            etiquetas.append(re.sub(' ', '\n', i))
        if len(i.split(' ')) == 3:
            etiquetas.append(re.sub(' ', '\n', i))
        if len(i.split(' ')) == 4:
            etiquetas.append(' '.join(i.split()[0:2])+'\n'+' '.join(i.split()[2:4]))
        if len(i.split(' ')) > 4:
            etiquetas.append(' '.join(i.split()[0:2])+'\n'+' '.join(i.split()[2:4])+'...')
    return etiquetas


#########################################################################


categorias = ['GO_BP.txt', 'GO_MF.txt', 'GO_CC.txt']
fdrs = [bpfdr, mffdr, ccfdr]


DESCRIPCIONES = {}
for c in categorias:
    # archivo 2
    file2 = open('data/'+c, 'r')
    terms_vias_genes = []
    for line in file2:
        line = line.rstrip()
        terms_vias_genes.append(line.split('\t'))
    file2.close()
    Terms_Vias_Genes = DataFrame(terms_vias_genes[1:], columns = ['base', 'Term'])
    description = Terms_Vias_Genes[['base', 'Term']].drop_duplicates()
    DESCRIPCIONES[c] = description



if anotacion_uniprot == '1':
    print('*****UniProtKB')
    no_anotadas_uniprot = enrichment_files(df = uniprot_entry_go_term)
    ###################
    filelocation1 = 'data/UniProt_Association.txt'
    filelocation3 = 'data/Background.txt'
    filelocation4 = 'data/List.txt'
    # archivo 1
    file1 = open(filelocation1, 'r')
    terms_vias_genes = []
    for line in file1:
        line = line.rstrip()
        terms_vias_genes.append(line.split('\t'))
    file1.close()
    Terms_Vias_Genes = DataFrame(terms_vias_genes[1:], columns = ['Entry', 'base'])
    association = Terms_Vias_Genes[['Entry', 'base']]
    #archivo 3
    file3 = open(filelocation3, 'r')
    background_file = []
    for line in file3:
        line = line.rstrip()
        background_file.append(line)
    file3.close()
    background = DataFrame(background_file[1:], columns = ['Entry'])
    #archivo 4
    file4 = open(filelocation4, 'r')
    condicion_file = []
    for line in file4:
        line = line.rstrip()
        condicion_file.append(line.split('\t'))
    file4.close()
    List = DataFrame(condicion_file[1:], columns = ['Entry'])
    ###################
    uniprot_enrich = {}
    uniprot_signif = {}
    for i, j in zip(categorias, fdrs):
        enrich = enrichment_analysis(BACK = background, LIST = List, ASSO = association, DESC = DESCRIPCIONES[i], FDR = j)
        uniprot_enrich[i.split('.')[0]] = enrich
        significantes = enrich.sort_values(by =['P'],ascending=True).reset_index(drop=True)
        significantes = significantes[significantes.Sig == 'T']
        uniprot_signif[i.split('.')[0]] = significantes
        print('Finished (UniProt):', i)
        #enrich['Short_Term'] = termino_corto(df = enrich)
        enrich.to_csv('data/UniProt_Enrichment_analysis_'+i.split('.')[0]+'.tsv', index=None,sep='\t')
    ###
    # los que no tienen terminos significantes se descartarán
    uni_info = list(np.repeat(go_uniptot_version, len(categorias)))
    uni_noanno = [no_anotadas_uniprot[1], no_anotadas_uniprot[1], no_anotadas_uniprot[1]]
    uni_database = ['UniProt', 'UniProt', 'UniProt']
    aprobados_uniprot = {}
    for i, j, k, l, m in zip(categorias, fdrs, uni_info, uni_noanno, uni_database):
        #print(i.split('.')[0])
        aprobados_uniprot[i.split('.')[0]] = filtro_significancia(df = uniprot_enrich[i.split('.')[0]],
                                      asso_file = i,
                                      fdr_val = j,
                                      info = k,
                                      no_annot = l,
                                      db = m)
else:
    pass
if anotacion_goa == '1':
    print('\n*****UniProt GOA')
    no_anotadas_goa = enrichment_files(df = goa_entry_go_term)
    ###################
    filelocation1 = 'data/GOA_Association.txt'
    filelocation3 = 'data/Background.txt'
    filelocation4 = 'data/List.txt'
    # archivo 1
    file1 = open(filelocation1, 'r')
    terms_vias_genes = []
    for line in file1:
        line = line.rstrip()
        terms_vias_genes.append(line.split('\t'))
    file1.close()
    Terms_Vias_Genes = DataFrame(terms_vias_genes[1:], columns = ['Entry', 'base'])
    GOA_association = Terms_Vias_Genes[['Entry', 'base']]
    #archivo 3
    file3 = open(filelocation3, 'r')
    background_file = []
    for line in file3:
        line = line.rstrip()
        background_file.append(line)
    file3.close()
    background = DataFrame(background_file[1:], columns = ['Entry'])
    #archivo 4
    file4 = open(filelocation4, 'r')
    condicion_file = []
    for line in file4:
        line = line.rstrip()
        condicion_file.append(line.split('\t'))
    file4.close()
    List = DataFrame(condicion_file[1:], columns = ['Entry'])
    ###################
    goa_enrich = {}
    goa_signif = {}
    for i, j in zip(categorias, fdrs):
        enrich = enrichment_analysis(BACK = background, LIST = List, ASSO = GOA_association, DESC = DESCRIPCIONES[i], FDR = j)
        goa_enrich[i.split('.')[0]] = enrich
        significantes = enrich.sort_values(by =['P'],ascending=True).reset_index(drop=True)
        significantes = significantes[significantes.Sig == 'T']
        goa_signif[i.split('.')[0]] = significantes
        print('Finished (GOA):', i)
        #enrich['Short_Term'] = termino_corto(df = enrich)
        enrich.to_csv('data/UniProtGOA_Enrichment_analysis_'+i.split('.')[0]+'.tsv', index=None,sep='\t')
    ###
    # los que no tienen terminos significantes se descartarán
    goa_info = list(np.repeat(goa_information, len(categorias)))
    goa_noanno = [no_anotadas_goa[1], no_anotadas_goa[1], no_anotadas_goa[1]]
    goa_database = ['UniProtGOA', 'UniProtGOA', 'UniProtGOA']
    aprobados_goa = {}
    for i, j, k, l, m in zip(categorias, fdrs, goa_info, goa_noanno, goa_database):
        #print(i.split('.')[0])
        aprobados_goa[i.split('.')[0]] = filtro_significancia(df = goa_enrich[i.split('.')[0]],
                                      asso_file = i,
                                      fdr_val = j,
                                      info = k,
                                      no_annot = l,
                                      db = m)
else:
    pass




cats = ['GO_BP', 'GO_MF', 'GO_CC']
###### UniProt ########################

if anotacion_uniprot == '1':
    go_tablas_uniprot = {}
    edges_frame_excel_uniprot = {}
    for z in cats:
        if aprobados_uniprot[z].count().iloc[0] > 1:
            df = aprobados_uniprot[z]
            df['Short_Term'] = termino_corto(df = aprobados_uniprot[z])
            
            significativos = []
            for x in df.base.drop_duplicates():
                dff = df[df.base == x]
                for index, row in dff.iterrows():
                    for i in row.entry.split(';'):
                        significativos.append([x, row.P, row.FDR, row.Term, row.Short_Term, i])
            gotabla = DataFrame(significativos, columns = ['GO', 'P', 'FDR', 'Term', 'Short_Term', 'Entry'])
            gotabla['LogminFDR'] = -np.log10(gotabla.FDR)
            gotabla['LogminP'] = -np.log10(gotabla.P)
            n = 0
            ranked = []
            for i in gotabla['Entry'].drop_duplicates():
                n+=1
                ranked.append([i, str(n)])
            rank = DataFrame(ranked, columns = ['Entry', 'label'])
            
            gotabla = gotabla.merge(rank, on = 'Entry', how = 'left')
            gotabla = gotabla.merge(no_anotadas_uniprot[0][['Entry', 'GO']], on = ['Entry', 'GO'], how = 'left')
            gotabla = gotabla.merge(uniprot_entry_go_term[['Entry', 'Gene']], on = 'Entry', how = 'left')
            gotabla = gotabla.merge(list_input[['Entry', 'values']], on = 'Entry', how = 'left')

            edges_frame_excel = gotabla[['GO','Entry', 'Gene', 'Term','values']]
            edges_frame_excel_uniprot[z] = edges_frame_excel
            if labelnode == 'Gene':
                gotabla = gotabla.rename({'Gene':'Entry', 'Entry':'Gene'}, axis='columns')
            if labelnode == 'UniProt':
                pass
            go_tablas_uniprot[z] = gotabla.drop_duplicates().reset_index(drop = True)
            del gotabla
            del edges_frame_excel
        else:
            if aprobados_uniprot[z].count().iloc[0] == 1:
                df = aprobados_uniprot[z]
                df['Short_Term'] = termino_corto(df = aprobados_uniprot[z])

                significativos = []
                for x in df.base.drop_duplicates():
                    dff = df[df.base == x]
                    for index, row in dff.iterrows():
                        for i in row.entry.split(';'):
                            significativos.append([x, row.P, row.FDR, row.Term, row.Short_Term, i])
                gotabla = DataFrame(significativos, columns = ['GO', 'P', 'FDR', 'Term', 'Short_Term', 'Entry'])
                gotabla['LogminFDR'] = -np.log10(gotabla.FDR)
                gotabla['LogminP'] = -np.log10(gotabla.P)
                n = 0
                ranked = []
                for i in gotabla['Entry'].drop_duplicates():
                    n+=1
                    ranked.append([i, str(n)])
                rank = DataFrame(ranked, columns = ['Entry', 'label'])

                gotabla = gotabla.merge(rank, on = 'Entry', how = 'left')
                gotabla = gotabla.merge(no_anotadas_uniprot[0][['Entry', 'GO']], on = ['Entry', 'GO'], how = 'left')
                gotabla = gotabla.merge(uniprot_entry_go_term[['Entry', 'Gene']], on = 'Entry', how = 'left')
                gotabla = gotabla.merge(list_input[['Entry', 'values']], on = 'Entry', how = 'left')

                edges_frame_excel = gotabla[['GO','Entry', 'Gene', 'Term','values']]
                edges_frame_excel_uniprot[z] = edges_frame_excel
                if labelnode == 'Gene':
                    gotabla = gotabla.rename({'Gene':'Entry', 'Entry':'Gene'}, axis='columns')
                if labelnode == 'UniProt':
                    pass
                go_tablas_uniprot[z] = gotabla.drop_duplicates().reset_index(drop = True)
                del gotabla
                del edges_frame_excel
        

###### GOA ########################
if anotacion_goa == '1':
    go_tablas_goa = {}
    edges_frame_excel_goa = {}
    for z in cats:
        if aprobados_goa[z].count().iloc[0] > 1:
            df = aprobados_goa[z]
            df['Short_Term'] = termino_corto(df = aprobados_goa[z])
            
            significativos = []
            for x in df.base.drop_duplicates():
                dff = df[df.base == x]
                for index, row in dff.iterrows():
                    for i in row.entry.split(';'):
                        significativos.append([x, row.P, row.FDR, row.Term, row.Short_Term, i])
            gotabla = DataFrame(significativos, columns = ['GO', 'P', 'FDR', 'Term', 'Short_Term', 'Entry'])
            gotabla['LogminFDR'] = -np.log10(gotabla.FDR)
            gotabla['LogminP'] = -np.log10(gotabla.P)
            n = 0
            ranked = []
            for i in gotabla['Entry'].drop_duplicates():
                n+=1
                ranked.append([i, str(n)])
            rank = DataFrame(ranked, columns = ['Entry', 'label'])
            
            gotabla = gotabla.merge(rank, on = 'Entry', how = 'left')
            gotabla = gotabla.merge(no_anotadas_goa[0][['Entry', 'GO']], on = ['Entry', 'GO'], how = 'left')
            gotabla = gotabla.merge(goa_entry_go_term[['Entry', 'Gene']], on = 'Entry', how = 'left')
            gotabla = gotabla.merge(list_input[['Entry', 'values']], on = 'Entry', how = 'left')

            edges_frame_excel = gotabla[['GO','Entry', 'Gene', 'Term','values']]
            edges_frame_excel_goa[z] = edges_frame_excel
            if labelnode == 'Gene':
                gotabla = gotabla.rename({'Gene':'Entry', 'Entry':'Gene'}, axis='columns')
            if labelnode == 'UniProt':
                pass
            go_tablas_goa[z] = gotabla.drop_duplicates().reset_index(drop = True)
        else:
            if aprobados_goa[z].count().iloc[0] == 1:
                df = aprobados_goa[z]
                df['Short_Term'] = termino_corto(df = aprobados_goa[z])

                significativos = []
                for x in df.base.drop_duplicates():
                    dff = df[df.base == x]
                    for index, row in dff.iterrows():
                        for i in row.entry.split(';'):
                            significativos.append([x, row.P, row.FDR, row.Term, row.Short_Term, i])
                gotabla = DataFrame(significativos, columns = ['GO', 'P', 'FDR', 'Term', 'Short_Term', 'Entry'])
                gotabla['LogminFDR'] = -np.log10(gotabla.FDR)
                gotabla['LogminP'] = -np.log10(gotabla.P)
                n = 0
                ranked = []
                for i in gotabla['Entry'].drop_duplicates():
                    n+=1
                    ranked.append([i, str(n)])
                rank = DataFrame(ranked, columns = ['Entry', 'label'])

                gotabla = gotabla.merge(rank, on = 'Entry', how = 'left')
                gotabla = gotabla.merge(no_anotadas_goa[0][['Entry', 'GO']], on = ['Entry', 'GO'], how = 'left')
                gotabla = gotabla.merge(goa_entry_go_term[['Entry', 'Gene']], on = 'Entry', how = 'left')
                gotabla = gotabla.merge(list_input[['Entry', 'values']], on = 'Entry', how = 'left')

                edges_frame_excel = gotabla[['GO','Entry', 'Gene', 'Term','values']]
                edges_frame_excel_goa[z] = edges_frame_excel
                if labelnode == 'Gene':
                    gotabla = gotabla.rename({'Gene':'Entry', 'Entry':'Gene'}, axis='columns')
                if labelnode == 'UniProt':
                    pass
                go_tablas_goa[z] = gotabla.drop_duplicates().reset_index(drop = True)


##############################################################################


from matplotlib import cm
from colormap import Colormap
import matplotlib


sequentials_colors = {'YlOrRd':cm.YlOrRd,'YlOrBr':cm.YlOrBr,'YlGnBu':cm.YlGnBu,
                      'YlGn':cm.YlGn,'Reds':cm.Reds,'PdPu':cm.RdPu,'Purples':cm.Purples,'PuRd':cm.PuRd,
                      'PuBuGn':cm.PuBuGn,'PuBu':cm.PuBu,'Oranges':cm.Oranges,'OrRd':cm.OrRd,
                      'Greys':cm.Greys,'Greens':cm.Greens,'GnBu':cm.GnBu,'BuPu':cm.BuPu,
                      'BuGn':cm.BuGn,'Blues':cm.Blues}

diverging_colors = {'GreBlaRed':Colormap().cmap_linear('green', 'black', 'red'),
                    'RedBlaGre':Colormap().cmap_linear('red', 'black', 'green'),
                    'RedBlaBlu':Colormap().cmap_linear('red', 'black', 'blue'),
                    'BluBlaRed':Colormap().cmap_linear('blue', 'black', 'red'),
                    'RedYlBlu':Colormap().cmap_linear('red', 'yellow', 'blue'),
                    'BluYlRed':Colormap().cmap_linear('blue', 'yellow', 'red'),
                      'seismic':cm.seismic,'coolwarm':cm.coolwarm,'bwr':cm.bwr,
                      'Spectral':cm.Spectral,'RdYlGn':cm.RdYlGn,'RdYlBu':cm.RdYlBu,
                      'RdGy':cm.RdGy,'RdBu':cm.RdBu,
                      'PuOr':cm.PuOr,'PiYG':cm.PiYG,'PRGn':cm.PRGn,'BrBG':cm.BrBG}

uniform_sequential = {'viridis':cm.viridis,'viridis_rev':cm.viridis.reversed(),
                      'plasma':cm.plasma,'plasma_rev':cm.plasma.reversed(),
                      'inferno':cm.inferno,'inferno_rev':cm.inferno.reversed(),
                      'magma':cm.magma,'magma_rev':cm.magma.reversed(),
                      'cividis':cm.cividis,'cividis_rev':cm.cividis.reversed()}

qualitative_colors = {'Pastel1':cm.Pastel1,'Pastel2':cm.Pastel2,'Paired':cm.Paired,
                      'Accent':cm.Accent,'Dark2':cm.Dark2,'Set1':cm.Set1,'Set2':cm.Set2,'Set3':cm.Set3,
                      'tab10':cm.tab10,'tab20':cm.tab20,'tab20b':cm.tab20b,'tab20c':cm.tab20c}

# estas rampas tienen una cantidad de colores predefinidos
tab20 = [matplotlib.colors.to_hex(i) for i in cm.tab20(np.arange(20)/20.)]
tab20b = [matplotlib.colors.to_hex(i) for i in cm.tab20b(np.arange(20)/20.)]
tab20c = [matplotlib.colors.to_hex(i) for i in cm.tab20c(np.arange(20)/20.)]
Set3 = [matplotlib.colors.to_hex(i) for i in cm.Set3(np.arange(12)/12.)]
Set2 = [matplotlib.colors.to_hex(i) for i in cm.Set2(np.arange(8)/8.)]
Set1 = [matplotlib.colors.to_hex(i) for i in cm.Set1(np.arange(9)/9.)]
Pastel2 = [matplotlib.colors.to_hex(i) for i in cm.Pastel2(np.arange(8)/8.)]
Pastel1 = [matplotlib.colors.to_hex(i) for i in cm.Pastel1(np.arange(9)/9.)]
Dark2 = [matplotlib.colors.to_hex(i) for i in cm.Dark2(np.arange(8)/8.)]
Paired = [matplotlib.colors.to_hex(i) for i in cm.Paired(np.arange(12)/12.)]
Accent = [matplotlib.colors.to_hex(i) for i in cm.Accent(np.arange(8)/8.)]
Spectral = [matplotlib.colors.to_hex(i) for i in cm.Spectral(np.arange(12)/12.)]

edge_colors = {'Colormap1':tab20 + tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral,
               'Colormap2':Spectral + tab20 + tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent,
               'Colormap3':Accent + Spectral + tab20 + tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired,
               'Colormap4':Paired + Accent + Spectral + tab20 + tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2,
               'Colormap5':Dark2 + Paired + Accent + Spectral + tab20 + tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1,
               'Colormap6':Pastel1 + Dark2 + Paired + Accent + Spectral + tab20 + tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2,
               'Colormap7':Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral + tab20 + tab20b + tab20c + Set3 + Set2 + Set1,
               'Colormap8':Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral + tab20 + tab20b + tab20c + Set3 + Set2,
               'Colormap9':Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral + tab20 + tab20b + tab20c + Set3,
               'Colormap10':Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral + tab20 + tab20b + tab20c,
               'Colormap11':tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral + tab20 + tab20b,
               'Colormap12':tab20b + tab20c + Set3 + Set2 + Set1 + Pastel2 + Pastel1 + Dark2 + Paired + Accent + Spectral + tab20}

sequentials_colors.update(diverging_colors)
sequentials_colors.update(uniform_sequential)
sequentials_colors.update(qualitative_colors)
sequentials_colors.update(edge_colors)





###############################################################################
# # Crear tablas de excel





def crear_excel(df = DataFrame([]), df_edges = DataFrame([]), info = '',
                asso_file = '', fdr_val = 0, no_annot = [], db = ''):
    results_sig = df[df.Sig == 'T']
    #
    gos = results_sig.base.drop_duplicates().tolist()
    lista_sup = re.sub(':', '%3A', '%2C'.join(gos))
    quickgo_url = 'https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/%7Bids%7D/chart?ids='
    quickgo = quickgo_url+lista_sup
    #
    reporte = {'base':[np.nan,
                           'GO DB Last-Modified',
                           'Input file name',
                           'Association file name',
                           'Total number of background',
                           'Total number of list',
                           'Background with GO Terms',
                           'List input with GO Terms',
                           'Non-singletons value for Bonf_corr',
                           'Correction Method',
                           'Value',
                           np.nan,
                           quickgo,
                           np.nan,
                           'Proteins with no information in UniProtKB',
                           ';'.join(no_annot)],
                'list_count':[np.nan,
                              info,
                              file_path,
                              asso_file,
                              int(float(df.tot_back.iloc[0:1])),
                              list_input['Entry'].drop_duplicates().count(),
                              df.tot_back.iloc[0],
                              df.tot_list.iloc[0],
                              int(float(df.Bonf_corr.iloc[-1:]) / float(df.P.iloc[-1:])),
                              'FDR',
                              str(fdr_val)+' ('+str(np.round(fdr_val * 100,1))+'%)',
                              np.nan,
                              'Copy and paste the url into your browser',
                              np.nan,
                              len(no_annot),
                              np.nan]}
    information = DataFrame(reporte)
    informe_final = pd.concat([results_sig, information], axis=0, sort=False).rename(columns={'base':'GO'})

    writer = pd.ExcelWriter(db+'_Enrichment_'+asso_file.split('.')[0]+'_FDR_'+str(fdr_val)+'.xlsx',
                           engine='xlsxwriter',options={'strings_to_urls': False})

    informe_final.to_excel(writer,'Significant GO Terms',index=False)

    df.to_excel(writer,'Enrichment Results',index=False)
    
    df_edges.drop_duplicates().to_excel(writer,'Edges Pathways',index=False)
    
    writer.save()
    





################ 
## UniProt
################
if anotacion_uniprot == '1':
    if ('GO_BP' in list(go_tablas_uniprot.keys())) == True:
        crear_excel(df = uniprot_enrich['GO_BP'],
                    df_edges = edges_frame_excel_uniprot['GO_BP'],
                    info = uni_info[0],
                    asso_file = categorias[0],
                    fdr_val = fdrs[0],
                    no_annot = uni_noanno[0],
                    db = uni_database[0])
    else:
        print('There are no enriched terms for BP in UniProtKB')
        pass
    if ('GO_MF' in list(go_tablas_uniprot.keys())) == True:
        crear_excel(df = uniprot_enrich['GO_MF'],
                    df_edges = edges_frame_excel_uniprot['GO_MF'],
                    info = uni_info[1],
                    asso_file = categorias[1],
                    fdr_val = fdrs[1],
                    no_annot = uni_noanno[1],
                    db = uni_database[1])
    else:
        print('There are no enriched terms for MF in UniProtKB')
        pass
    if ('GO_CC' in list(go_tablas_uniprot.keys())) == True:
        crear_excel(df = uniprot_enrich['GO_CC'],
                    df_edges = edges_frame_excel_uniprot['GO_CC'],
                    info = uni_info[2],
                    asso_file = categorias[2],
                    fdr_val = fdrs[2],
                    no_annot = uni_noanno[2],
                    db = uni_database[2])
    else:
        print('There are no enriched terms for CC in UniProtKB')
        pass
################ 
## GOA
################
if anotacion_goa == '1':
    if ('GO_BP' in list(go_tablas_goa.keys())) == True:
        crear_excel(df = goa_enrich['GO_BP'],
                    df_edges = edges_frame_excel_goa['GO_BP'],
                    info = goa_info[0],
                    asso_file = categorias[0],
                    fdr_val = fdrs[0],
                    no_annot = goa_noanno[0],
                    db = goa_database[0])
    else:
        print('There are no enriched terms for BP in GOA')
        pass
    if ('GO_MF' in list(go_tablas_goa.keys())) == True:
        crear_excel(df = goa_enrich['GO_MF'],
                    df_edges = edges_frame_excel_goa['GO_MF'],
                    info = goa_info[1],
                    asso_file = categorias[1],
                    fdr_val = fdrs[1],
                    no_annot = goa_noanno[1],
                    db = goa_database[1])
    else:
        print('There are no enriched terms for MF in GOA')
        pass
    if ('GO_CC' in list(go_tablas_goa.keys())) == True:
        crear_excel(df = goa_enrich['GO_CC'],
                    df_edges = edges_frame_excel_goa['GO_CC'],
                    info = goa_info[2],
                    asso_file = categorias[2],
                    fdr_val = fdrs[2],
                    no_annot = goa_noanno[2],
                    db = goa_database[2])
    else:
        print('There are no enriched terms for CC in GOA')
        pass




# # funcion para crear todas las redes

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import ListedColormap, LinearSegmentedColormap


def create_plots(XXXXXXXXXX = DataFrame([]),
                 YYYYYYYYYY = DataFrame([]),
                 title = '',
                 localizacion = '',
                 bar_title = ''):
    matrix = XXXXXXXXXX.pivot_table(values='Entry',index=['label'],aggfunc=len,columns=['GO', 'Term', 'Short_Term'])
    df_mat = []
    for i in list(matrix.columns.values):
        new = DataFrame(matrix[i])
        for x, y in zip(list(new[i].index), list(new[i].values)):
            df_mat.append([x, i, y])
    df_mat = DataFrame(df_mat, columns = ['go0', 'go1', 'val']).dropna()
    nodos = []
    for index, row in df_mat.iterrows():
        if row.go0 == row.go1:
            #print(row.go0, row.go1)
            continue
        else:
            #print(row.go0, row.go1)
            nodos.append([row.go0, row.go1, row.val])
    nodos = DataFrame(nodos)
    nodos = DataFrame([[i for i in nodos[0]],
                       [i[0] for i in nodos[1]],
                        nodos[2]]).T
    G=nx.Graph()
    for index, row in nodos.iterrows():
        G.add_edge(str(row[0]), row[1],weight = row[2])
    #esmall=[(u,v,d['weight']) for (u,v,d) in G.edges(data=True) if d['weight'] > 0]
    xxx = []
    for i in G.nodes():
        xxx.append(str(i))
    yyy = DataFrame(xxx, columns = ['label'])
    # si hay columna de valores numéricos en el input
    if 'values' in list(list_input.select_dtypes('number').columns):
        zzz = yyy.merge(XXXXXXXXXX[['label', 'values']], on = 'label', how = 'left').drop_duplicates().reset_index(drop = True)
        zzz = zzz.sort_values(by ='values',ascending=False).reset_index(drop=True)
    else:
        zzz = yyy.merge(XXXXXXXXXX[['label']], on = 'label', how = 'left').drop_duplicates().reset_index(drop = True)
    G=nx.Graph()
    for index, row in nodos.iterrows():
        G.add_edge(str(row[0]), row[1],weight = row[2])
    #esmall=[(u,v,d['weight']) for (u,v,d) in G.edges(data=True) if d['weight'] > 0]
    xxx = []
    for i in G.nodes():
        xxx.append(str(i))
    yyy = DataFrame(xxx, columns = ['label'])
    zzz = yyy.merge(XXXXXXXXXX[['label', 'values']], on = 'label', how = 'left').drop_duplicates().reset_index(drop = True)
    zzz = zzz.sort_values(by ='values',ascending=False).reset_index(drop=True)
    ###################
    mycmap = sequentials_colors[colormap_definido].reversed()
    nulos = len(zzz['values']) - len(zzz['values'].dropna())
    null_col = list(np.repeat('', nulos))
    ids = list(np.round(np.linspace(zzz['values'].max(), zzz['values'].min(), len(zzz['values'])*4), 50))
    rangoforcolor = []
    valor_unico = []
    n = ids[0]
    for i in ids:
        if i == n:
            valor_unico.append(i)
            continue
        rangoforcolor.append([n, i])
        n = i
    #*******************************************************
    mycmap0 = mycmap(np.linspace(0, 1, len(rangoforcolor)))
    ##*********************************************************
    colores = []
    for i in mycmap0:
        colores.append(matplotlib.colors.to_hex(i))
    rangos = {}
    for k, j in zip(rangoforcolor, colores):
        if len(k) == 2:
            rangos[str(k[0])+','+str(k[1])] = j
        if len(k) == 1:
            rangos[str(k[0])] = j   
    if len(set(zzz.dropna()['values'].tolist())) == 1:
        zzz['cols'] = list(np.repeat(nodecolorsinback, len(zzz['values'].dropna()))) + null_col
    else:
        positivos = []
        for i in rangoforcolor:
            if len(i) == 2:
                for j in [(np.round(x, 50), X) for x, X in zip(zzz['values'], zzz.label) if x > 0]: #[np.round(x, 50) for x in zzz['values'] if x > 0]:
                    if i[0] >= j[0] >= i[1]:
                        positivos.append([j[1], rangos[str(i[0])+','+str(i[1])]])
        if positivos == []:
            pass
        else:
            positivos = DataFrame(positivos).drop_duplicates()[1].tolist()
        negativos = []
        for i in rangoforcolor:
            if len(i) == 2:
                for j in [(np.round(x, 50), X) for x, X in zip(zzz['values'], zzz.label) if x < 0]: #[np.round(x, 50) for x in zzz['values'] if x < 0]:
                    if i[0] >= j[0] >= i[1]:
                        negativos.append([j[1], rangos[str(i[0])+','+str(i[1])]])
        if negativos == []:
            pass
        else:
            negativos = DataFrame(negativos).drop_duplicates()[1].tolist()
        zzz['cols'] = positivos + negativos + null_col
        ######
    n = 0
    l = 10
    k = 15
    for i in range(10):
        if n+1 <= len(G.edges()) <= l:
            #print(k)
            valor = k
        #print(n+1, k, l)
        n += 10
        l += 10
        k -= 1
    if 101 <= len(G.edges()) <= 200:
        valor = 5
    if 201 <= len(G.edges()) <= 300:
        valor = 4
    if len(G.edges()) >= 301:
        valor = 3
    ####
    if hayvalores == 'nohayvalores':
        colorletra = nodecolorsinback
    else:
        colorletra = 'none'
    #################
    # asignacion de colores a cada entry, menos a terms
    colorder = dict(zip(zzz.label.tolist(), zzz.cols.tolist()))
    # posiciones en el plano cartesiano
    #pos = nx.spring_layout(G,iterations=50) #nx.spring_layout(G, k = 0.3, iterations=50, threshold=0.001, seed= 123)
    pos = nx.kamada_kawai_layout(G, dist=None, weight='weight', scale=1, center=None, dim=2)
    #pos = nx.circular_layout(G)
    # ordenados por FDR
    gos = YYYYYYYYYY.base.drop_duplicates().tolist()
    labnodeterms = dict(zip(gos, edge_colors[usercolormap][0:len(gos)]))
    name_term = dict(zip(gos, YYYYYYYYYY.Term.drop_duplicates().tolist()))
    # size de nodo, amplificado 200 veces
    sizenodo = -np.log10(np.array(YYYYYYYYYY.FDR))
    
    ######################################
    if labelnode == 'Gene':
        genelist = []
        for i in gos:
            df = XXXXXXXXXX[XXXXXXXXXX.GO == i]
            geneslist = (df.label.tolist(), df.Gene.tolist())
            genelist.append([i, geneslist])
        links_for_entrys = {}
        for i in genelist:
            for j, k in zip(i[1][0], i[1][1]):
                links_for_entrys[j] = [k, 'https://www.uniprot.org/uniprot/'+k]
        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    if labelnode == 'UniProt':
        genelist = []
        for i in gos:
            df = XXXXXXXXXX[XXXXXXXXXX.GO == i]
            geneslist = (df.label.tolist(), df.Entry.tolist())
            genelist.append([i, geneslist])
        links_for_entrys = {}
        for i in genelist:
            for j, k in zip(i[1][0], i[1][1]):
                links_for_entrys[j] = [k, 'https://www.uniprot.org/uniprot/'+k]
    ###########################################
    url_for_go_uniprot_quickgo = {}
    for i in gos:
        fijo = 'https://www.ebi.ac.uk/QuickGO/term/'+i
        url_for_go_uniprot_quickgo[i] = fijo
    ####
    valor_maximo = zzz['values'].max().round()
    valor_minimo = zzz['values'].min().round()
    verti = []
    for i, j in G.edges():
        if i in gos:
            verti.append(labnodeterms[i])
        if j in gos:
            verti.append(labnodeterms[j])
    ccc = []
    for i in G.nodes():
        if i in list(labnodeterms.keys()):
            ccc.append(labnodeterms[i])
        else:
            continue
    #
    acumulacion = ''
    ##############################################################################
    #>>>>>>>>>>    1 y 2
    ##############################################################################
    NEWSIZE = [valor, 0]
    NEWPAD = [0.1, valor*0.7]
    NEWCOLOR = ['white', colorletra]
    IMGLABEL = [1, 2]
    for newsize, newpad, newcolor, imglabel in zip(NEWSIZE, NEWPAD, NEWCOLOR, IMGLABEL):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(G, pos, nodelist = gos,
                               node_size =  list(np.array(sizenodo) * 150),
                               node_shape = 'o',
                               node_color = edge_colors[usercolormap][0:len(gos)],
                               linewidths = 0.5, edgecolors= 'white')
        nx.draw_networkx_edges(G, pos, width = 1.5, alpha= 0.5, edge_color= verti)
        ax.axis('equal')
        for nod_entry in links_for_entrys:
            ax.annotate(nod_entry,
                        xy=pos[nod_entry], xycoords='data',
                        url = links_for_entrys[nod_entry][1],
                        xytext=pos[nod_entry], textcoords='data',
                        color = newcolor, #..................................
                        fontweight='bold',
                        size = newsize, #..................................
                        ha='center', va="center",
                        bbox=dict(boxstyle="circle",
                                  pad = newpad, #..................................
                                  alpha=1, fc=colorder[nod_entry],
                        ec="none", url = links_for_entrys[nod_entry][1]))
        ax.axis('off')    
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax2 = fig.add_axes([0.5, 0.77, 0.015, .18]) # vertical
        if len(valor_unico) > 1:
            ax2.axis('off')
            posiciones_leyenda_de_abajo = [.5, 0.2, 0.15, 0.73]
            pass
        else:
            norm = mpl.colors.Normalize(vmax = valor_maximo,
                                        vmin = valor_minimo)
            cb1 = mpl.colorbar.ColorbarBase(ax2,
                                            cmap=ListedColormap(mycmap(np.linspace(1, 0, len(zzz['values'])*2))),
                                            norm=norm, spacing='proportional',
                                            orientation='vertical')
            plt.tick_params(axis="y", color="grey")
            cb1.set_label(bar_title, labelpad=-30, y=1.2, rotation=0, size=10, fontweight='bold')
            plt.yticks(size = 7)
            cb1.outline.set_linewidth(0)
            posiciones_leyenda_de_abajo = [0.5, 0, 0.15, 0.73]
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes(posiciones_leyenda_de_abajo)    
        ax3.text(0,0.95, title, size=12,ha='left',color= 'black', fontweight='bold')
        n = 0.05
        for t in gos[0:20]:
            n += 0.043
            ax3.annotate(t,
                        xy=np.array([0,1-n]), xycoords='data',
                        url = url_for_go_uniprot_quickgo[t],
                        xytext=np.array([0,1-n]), textcoords='data',
                        size=8, ha='left', va="center",
                        bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[t], ec="none",
                                 url = url_for_go_uniprot_quickgo[t]))
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
        
    ##############################################################################
    #>>>>>>>>>>    3 y 4
    ##############################################################################
    IMGLABEL = [3, 4]
    for newsize, newpad, newcolor, imglabel in zip(NEWSIZE, NEWPAD, NEWCOLOR, IMGLABEL):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(G, pos, nodelist = gos,
                               node_size =  list(np.array(sizenodo) * 150),
                               node_shape = 'o',
                               node_color = edge_colors[usercolormap][0:len(gos)],
                               linewidths = 0.5, edgecolors= 'white')
        nx.draw_networkx_edges(G, pos, width = 1.5, alpha= 0.5, edge_color= verti)
        ax.axis('equal')
        for nod_entry in links_for_entrys:
            ax.annotate(nod_entry,
                        xy=pos[nod_entry], xycoords='data',
                        url = links_for_entrys[nod_entry][1],
                        xytext=pos[nod_entry], textcoords='data',
                        color = newcolor, #..................................
                        fontweight='bold',
                        size = newsize, #..................................
                        ha='center', va="center",
                        bbox=dict(boxstyle="circle",
                                  pad = newpad, #..................................
                                  alpha=1, fc=colorder[nod_entry],
                        ec="none", url = links_for_entrys[nod_entry][1]))
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax2 = fig.add_axes([0.5, 0.77, 0.015, .18]) # vertical
        if len(valor_unico) > 1:
            ax2.axis('off')
            posiciones_leyenda_de_abajo = [.5, 0.2, 0.15, 0.73]
            pass
        else:
            norm = mpl.colors.Normalize(vmax = valor_maximo,
                                        vmin = valor_minimo)
            cb1 = mpl.colorbar.ColorbarBase(ax2,
                                            cmap=ListedColormap(mycmap(np.linspace(1, 0, len(zzz['values'])*2))),
                                            norm=norm, spacing='proportional',
                                            orientation='vertical')
            plt.tick_params(axis="y", color="grey")
            cb1.set_label(bar_title, labelpad=-30, y=1.2, rotation=0, size=10, fontweight='bold')
            plt.yticks(size = 7)
            cb1.outline.set_linewidth(0)
            posiciones_leyenda_de_abajo = [0.5, 0, 0.15, 0.73]
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes(posiciones_leyenda_de_abajo)
        ax3.text(0,0.95, title, size=12,ha='left',color= 'black', fontweight='bold')
        n = 0.05
        for t in gos[0:20]:
            n += 0.043
            ax3.annotate(name_term[t],
                        xy=np.array([0,1-n]), xycoords='data',
                        url = url_for_go_uniprot_quickgo[t],
                        xytext=np.array([0,1-n]), textcoords='data',
                        size=8, ha='left', va="center",
                        bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[t], ec="none",
                                 url = url_for_go_uniprot_quickgo[t]))
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
    
    ##############################################################################
    #>>>>>>>>>>    5 y 6
    ##############################################################################
    label_gene = {}
    for i, j in zip(XXXXXXXXXX.label.tolist(), XXXXXXXXXX.Entry.tolist()):
        label_gene[i] = [i, j]
    
    IMGLABEL = [5, 6]
    for tipo_label, imglabel, sizlab in zip([0, 1], IMGLABEL, [valor, valor * 0.7]):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(G, pos, nodelist = gos,
                               node_size =  list(np.array(sizenodo) * 150),
                               node_shape = 'o',
                               node_color = edge_colors[usercolormap][0:len(gos)],
                               linewidths = 0.5, edgecolors= 'white')
        nx.draw_networkx_edges(G, pos, width = 1.5, alpha= 0.5, edge_color= verti)
        ax.axis('equal')
        for nod_entry in label_gene:
            ax.annotate(label_gene[nod_entry][tipo_label],
                        xy=pos[nod_entry], xycoords='data',
                        url = links_for_entrys[nod_entry][1], #rotation=45,
                        xytext=pos[nod_entry],textcoords='data',
                        color=colorder[nod_entry],
                        #fontweight='bold',
                        size=sizlab,
                        ha='center', va="center",
                        bbox=dict(boxstyle="Square",
                                  pad=0.1,
                                  alpha=0.1, fc='whitesmoke',
                        ec="none", url = links_for_entrys[nod_entry][1]))
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax2 = fig.add_axes([0.5, 0.77, 0.015, .18]) # vertical
        if len(valor_unico) > 1:
            ax2.axis('off')
            posiciones_leyenda_de_abajo = [.5, 0.2, 0.15, 0.73]
            pass
        else:
            norm = mpl.colors.Normalize(vmax = valor_maximo,
                                        vmin = valor_minimo)
            cb1 = mpl.colorbar.ColorbarBase(ax2,
                                            cmap=ListedColormap(mycmap(np.linspace(1, 0, len(zzz['values'])*2))),
                                            norm=norm, spacing='proportional',
                                            orientation='vertical')
            plt.tick_params(axis="y", color="grey")
            cb1.set_label(bar_title, labelpad=-30, y=1.2, rotation=0, size=10, fontweight='bold')
            plt.yticks(size = 7)
            cb1.outline.set_linewidth(0)
            posiciones_leyenda_de_abajo = [0.5, 0, 0.15, 0.73]
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes(posiciones_leyenda_de_abajo)
        ax3.text(0,0.95, title, size=12,ha='left',color= 'black', fontweight='bold')
        n = 0.05
        for t in gos[0:20]:
            n += 0.043
            ax3.annotate(name_term[t],
                         xy=np.array([0,1-n]), xycoords='data',
                         url = url_for_go_uniprot_quickgo[t],
                         xytext=np.array([0,1-n]), textcoords='data',
                         size=8, ha='left', va="center",
                         bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[t], ec="none",
                                   url = url_for_go_uniprot_quickgo[t]))
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
    
    ##############################################################################
    #>>>>>>>>>>    7 y 8
    ##############################################################################
    columnas = ['GO','LogminP', 'LogminFDR', 'Entry']
    frame1 = DataFrame(XXXXXXXXXX[columnas].drop_duplicates()              .groupby(['GO', 'LogminP', 'LogminFDR']).Entry.count()).reset_index()
    frame1['constante'] = -np.log10(0.05)
    frame1 = frame1.sort_values(by ='LogminP',ascending=False).reset_index(drop=True)
    col_font_annotate = {}
    for i, j in zip(gos, np.repeat('black', len(gos))):
        col_font_annotate[i] = j
    
    # solo se mostraran unicamente las 20 primeras
    if len(frame1) <= 20:
        faltantes = 20 - len(frame1)
        barras_vacias = []
        add_to_labnodeterms = {}
        links_perdidos = {}
        for i in range(faltantes):
            barras_vacias.append([str(i),None, None,None,-np.log10(0.05)])
            labnodeterms.update({str(i):'white'}) # actualizo el dict anterior
            add_to_labnodeterms[str(i)] = 'white'
            links_perdidos[str(i)] = None
            col_font_annotate.update({str(i):'white'}) # actualizo el dict anterior
            empty = DataFrame(barras_vacias, columns = ['GO','LogminP','LogminFDR','Entry', 'constante']) 
        frame2 = frame1.sort_values(by ='LogminP',ascending=True).reset_index(drop=True)
        frame3 = pd.concat([empty, frame2])
        url_for_go_uniprot_quickgo.update(links_perdidos) # este dicts se actualizan si es que hay menos de 20 terms
        name_term.update(links_perdidos) # este dicts se actualizan si es que hay menos de 20 terms
    if len(frame1) >= 21:
        frame2 = frame1.iloc[0:20]
        frame3 = frame2.sort_values(by ='LogminP',ascending=True).reset_index(drop=True)
    
    
    def bar_parameters(df = DataFrame([]), colum_val = 1, column_lab = 0):
        ejey = list(df.iloc[0:len(df),colum_val])
        ejex = list(df.iloc[0:len(df),column_lab])
        return ejex, ejey

    valores_constantes = frame3.constante.tolist()
    logaritmo_fdr = frame3.LogminFDR.tolist()
    cuentas_entry = frame3.Entry.tolist()
    
    IMGLABEL = [7, 8]
    for newsize, newpad, newcolor, imglabel in zip(NEWSIZE, NEWPAD, NEWCOLOR, IMGLABEL):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(G, pos, nodelist = gos,
                               node_size =  list(np.array(sizenodo) * 200),
                               node_shape = 'o',
                               node_color = edge_colors[usercolormap][0:len(gos)],
                               linewidths = 0.5, edgecolors= 'white')
        nx.draw_networkx_edges(G, pos, width = 2, alpha= 0.5, edge_color= verti)
        ax.axis('equal')
        for nod_entry in links_for_entrys:
            ax.annotate(nod_entry,
                        xy=pos[nod_entry], xycoords='data',
                        url = links_for_entrys[nod_entry][1],
                        xytext=pos[nod_entry], textcoords='data',
                        color = newcolor, #..................................
                        fontweight='bold',
                        size = newsize, #..................................
                        ha='center', va="center",
                        bbox=dict(boxstyle="circle",
                                  pad = newpad, #..................................
                                  alpha=1, fc=colorder[nod_entry],
                        ec="none", url = links_for_entrys[nod_entry][1]))
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax2 = fig.add_axes([0.5, 0.77, 0.015, .18]) # vertical
        if len(valor_unico) > 1:
            ax2.axis('off')
            posiciones_leyenda_de_abajo = [.5, 0.2, 0.5, 0.7]
            pass
        else:
            norm = mpl.colors.Normalize(vmax = valor_maximo,
                                        vmin = valor_minimo)
            cb1 = mpl.colorbar.ColorbarBase(ax2,
                                            cmap=ListedColormap(mycmap(np.linspace(1, 0, len(zzz['values'])*2))),
                                            norm=norm, spacing='proportional',
                                            orientation='vertical')
            plt.tick_params(axis="y", color="grey")
            cb1.set_label(bar_title, labelpad=-30, y=1.2, rotation=0, size=10, fontweight='bold')
            plt.yticks(size = 7)
            cb1.outline.set_linewidth(0)
            posiciones_leyenda_de_abajo = [0.5, 0, 0.5, 0.7]
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes(posiciones_leyenda_de_abajo)    
        ejes = bar_parameters(df = frame3)
        plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
        plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True
        h = 0
        for i, j, k in zip(ejes[0] , ejes[1], cuentas_entry):
            # barras
            ax3.barh(i, j, height= 0.8,
                        color= labnodeterms[i],
                        align='center',
                        linewidth = 0,
                        alpha = 1)
            # valores
            ax3.annotate(' '+str(k),
                        xy= np.array([0 + j, h]), xycoords='data', #(rect.get_x() + rect.get_width() / 2, height),
                        xytext=np.array([0 + j, h]), textcoords='data',  # 3 points vertical offset
                        size=7, ha='left', va='center')
            ax3.annotate(i,
                        xy=np.array([-0.2, h]), xycoords='data',
                        url = url_for_go_uniprot_quickgo[i], color = col_font_annotate[i],
                        xytext=np.array([-0.2, h]), textcoords='data',
                        size=7, ha='right', va="center",# fontweight='bold',
                        bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[i],
                                  url = url_for_go_uniprot_quickgo[i], ec="none"))        
            h +=1
        ax3.plot(np.array(valores_constantes), np.array(list(range(0,20))),
                 color = 'white',linewidth=0.5, zorder=1)
        ax3.scatter(np.array(valores_constantes), np.array(list(range(0,20))),
                 s=5,c='white', marker='s', zorder=2)
        ax3.plot(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 color = 'blue',linewidth=0.5)
        ax3.scatter(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 s=5,c='blue', marker='o', zorder=2)
        plt.text(0, 21, "       "+title+"\n\nP-value & Ajusted P-value",size= 8,fontweight='bold')
        # configuracionmanual de la escala
        scala = list(range(0,300+1, 2)) # escala prdeterminada, independiente de los valores
        q=0
        w=2
        for i in range(len(scala)): # este bucle encuentra el valor maximo dentro de la escala predeterminada
            if q <= frame2.LogminP.max() <= w:
                val_max_to_scala = w
                break
            q+=2
            w+=2
        ax3.plot([0, val_max_to_scala], [19.8, 19.8], color = 'black',linewidth=0.3, zorder=1)
        for i in list(range(0, val_max_to_scala+1,2)):
            plt.text(i, 20.2, str(i), size= 6, ha='center')
            plt.text(i, 19.8, '|', size= 4, ha='center')
        if val_max_to_scala > 30:
            plt.xticks([-2.5] + [val_max_to_scala*1.5], size=6, color='black')
        else:
            plt.xticks([-2.5] + [val_max_to_scala*3], size=6, color='black')
        plt.yticks(color='none') # oculta las etiquetas del eje y
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
        
    ##############################################################################
    #>>>>>>>>>>    9 y 10
    ##############################################################################
    IMGLABEL = [9, 10]
    for tipo_label, newsize, newpad, newcolor, imglabel in zip([0, 1], [valor, valor * 0.6], [0.1, 0.1],
                                                               ['white', 'white'], IMGLABEL):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(G, pos, nodelist = gos,
                               node_size =  list(np.array(sizenodo) * 200),
                               node_shape = 'o',
                               node_color = edge_colors[usercolormap][0:len(gos)],
                               linewidths = 0.5, edgecolors= 'white')
        nx.draw_networkx_edges(G, pos, width = 2, alpha= 0.5, edge_color= verti)
        ax.axis('equal')
        for nod_entry in links_for_entrys:
            ax.annotate(label_gene[nod_entry][tipo_label],
                        xy=pos[nod_entry], xycoords='data',
                        url = links_for_entrys[nod_entry][1],
                        xytext=pos[nod_entry], textcoords='data',
                        color = newcolor, #..................................
                        #fontweight='bold',
                        size = newsize, #..................................
                        ha='center', va="center",
                        bbox=dict(boxstyle="round",
                                  #pad = newpad, #..................................
                                  alpha=1, fc=colorder[nod_entry],
                        ec="none", url = links_for_entrys[nod_entry][1]))
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax2 = fig.add_axes([0.5, 0.77, 0.015, .18]) # vertical
        if len(valor_unico) > 1:
            ax2.axis('off')
            posiciones_leyenda_de_abajo = [.5, 0.2, 0.5, 0.7]
            pass
        else:
            norm = mpl.colors.Normalize(vmax = valor_maximo,
                                        vmin = valor_minimo)
            cb1 = mpl.colorbar.ColorbarBase(ax2,
                                            cmap=ListedColormap(mycmap(np.linspace(1, 0, len(zzz['values'])*2))),
                                            norm=norm, spacing='proportional',
                                            orientation='vertical')
            plt.tick_params(axis="y", color="grey")
            cb1.set_label(bar_title, labelpad=-30, y=1.2, rotation=0, size=10, fontweight='bold')
            plt.yticks(size = 7)
            cb1.outline.set_linewidth(0)        
            posiciones_leyenda_de_abajo = [0.5, 0, 0.5, 0.7]
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes(posiciones_leyenda_de_abajo)
        ejes = bar_parameters(df = frame3)
        plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
        plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True
        h = 0
        for i, j, k in zip(ejes[0] , ejes[1], cuentas_entry):
            # barras
            ax3.barh(i, j, height= 0.8,
                        color= labnodeterms[i],
                        align='center',
                        linewidth = 0,
                        alpha = 1)
            # valores
            ax3.annotate(' '+str(k),
                        xy= np.array([0 + j, h]), xycoords='data', #(rect.get_x() + rect.get_width() / 2, height),
                        xytext=np.array([0 + j, h]), textcoords='data',  # 3 points vertical offset
                        size=7, ha='left', va='center')
            ax3.annotate(i,
                        xy=np.array([-0.2, h]), xycoords='data',
                        url = url_for_go_uniprot_quickgo[i], color = col_font_annotate[i],
                        xytext=np.array([-0.2, h]), textcoords='data',
                        size=7, ha='right', va="center",# fontweight='bold',
                        bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[i],
                                  url = url_for_go_uniprot_quickgo[i], ec="none"))
            h +=1
        ax3.plot(np.array(valores_constantes), np.array(list(range(0,20))),
                 color = 'white',linewidth=0.5, zorder=1)
        ax3.scatter(np.array(valores_constantes), np.array(list(range(0,20))),
                 s=5,c='white', marker='s', zorder=2)
        ax3.plot(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 color = 'blue',linewidth=0.5)
        ax3.scatter(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 s=5,c='blue', marker='o', zorder=2)
        plt.text(0, 21, "       "+title+"\n\nP-value & Ajusted P-value",size= 8,fontweight='bold')
        # configuracionmanual de la escala
        scala = list(range(0,300+1, 2)) # escala prdeterminada, independiente de los valores
        q=0
        w=2
        for i in range(len(scala)): # este bucle encuentra el valor maximo dentro de la escala predeterminada
            if q <= frame2.LogminP.max() <= w:
                val_max_to_scala = w
                break
            q+=2
            w+=2
        ax3.plot([0, val_max_to_scala], [19.8, 19.8], color = 'black',linewidth=0.3, zorder=1)
        for i in list(range(0, val_max_to_scala+1,2)):
            plt.text(i, 20.2, str(i), size= 6, ha='center')
            plt.text(i, 19.8, '|', size= 4, ha='center')
        if val_max_to_scala > 30:
            plt.xticks([-2.5] + [val_max_to_scala*1.5], size=6, color='black')
        else:
            plt.xticks([-2.5] + [val_max_to_scala*3], size=6, color='black')    
        plt.yticks(color='none') # oculta las etiquetas del eje y
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')   
        plt.close()
            
    ##############################################################################
    #>>>>>>>>>>    11 y 12
    ##############################################################################
    IMGLABEL = [11, 12]
    for lll, imglabel in zip([0, 1], IMGLABEL):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, 1, 1])
        ejes = bar_parameters(df = frame3)
        plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
        plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True
        h = 0
        for i, j, k in zip(ejes[0] , ejes[1], cuentas_entry):
            # barras
            ax.barh(i, j, height= 0.8,
                        color= labnodeterms[i],
                        align='center',
                        linewidth = 0,
                        alpha = 1)
            # valores
            ax.annotate(' '+str(k),
                        xy= np.array([0 + j, h]), xycoords='data', #(rect.get_x() + rect.get_width() / 2, height),
                        xytext=np.array([0 + j, h]), textcoords='data',  # 3 points vertical offset
                        size=9, ha='left', va='center')
            if lll == 0:
                ax.annotate(name_term[i],
                            xy=np.array([-0.2, h]), # espacio entre la barra y el path term
                            xycoords='data',
                            url = url_for_go_uniprot_quickgo[i], color = col_font_annotate[i],
                            xytext=np.array([-0.2, h]), textcoords='data',
                            size=9, ha='right', va="center",# fontweight='bold',
                            bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[i],
                                      url = url_for_go_uniprot_quickgo[i], ec="none"))
            if lll == 1:
                ax.annotate(name_term[i],
                            xy=np.array([-0.2, h]), # espacio entre la barra y el path term
                            xycoords='data',
                            url = url_for_go_uniprot_quickgo[i], color = col_font_annotate[i],
                            xytext=np.array([-0.2, h]), textcoords='data',
                            size=9, ha='right', va="center",# fontweight='bold',
                            bbox=dict(boxstyle="round", alpha=0.1, fc='whitesmoke',
                                      url = url_for_go_uniprot_quickgo[i], ec="none"))
            h +=1
        ax.plot(np.array(valores_constantes), np.array(list(range(0,20))),
                 color = 'white',linewidth=0.5, zorder=1)
        ax.scatter(np.array(valores_constantes), np.array(list(range(0,20))),
                 s=5,c='white', marker='s', zorder=2)
        ax.plot(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 color = 'blue',linewidth=0.5)
        ax.scatter(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 s=5,c='blue', marker='o', zorder=2)
        plt.text(0, 21, "       "+title+"\n\nP-value & Ajusted P-value",size= 9,fontweight='bold')
        # configuracionmanual de la escala
        scala = list(range(0,300+1, 2)) # escala prdeterminada, independiente de los valores
        q=0
        w=2
        for i in range(len(scala)): # este bucle encuentra el valor maximo dentro de la escala predeterminada
            if q <= frame2.LogminP.max() <= w:
                val_max_to_scala = w
                break
            q+=2
            w+=2
        ax.plot([0, val_max_to_scala], [19.8, 19.8], color = 'black',linewidth=0.3, zorder=1)
        for i in list(range(0, val_max_to_scala+1,2)):
            plt.text(i, 20.2, str(i), size= 6, ha='center')
            plt.text(i, 19.8, '|', size= 4, ha='center')
        if val_max_to_scala > 30:
            plt.xticks([-15] + [val_max_to_scala*1.5], size=6, color='black')
        else:
            plt.xticks([-15] + [val_max_to_scala*3], size=6, color='black')
        plt.yticks(list(range(1,25)), color='none') # aumento el margen superior para mostrar el titulo
        #plt.yticks(color='none') # oculta las etiquetas del eje y
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Bar_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Bar_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
                
    ##############################################################################
    #>>>>>>>>>>    13 y 14
    ##############################################################################
    frame4 = frame3.sort_values(by ='Entry',ascending=False).reset_index(drop=True)
    for_pie = bar_parameters(df = frame4.dropna(), colum_val = 3, column_lab = 0)
    ######
    if len(gos) < 6:
        sizepielabel = 20
    if 6 <= len(gos) < 8:
        sizepielabel = 18
    if len(gos) == 8:
        sizepielabel = 16
    if 9 <= len(gos) < 11:
        sizepielabel = 14
    if 11 <= len(gos) < 13:
        sizepielabel = 12
    if 13 <= len(gos) < 15:
        sizepielabel = 10
    if len(gos) >= 15:
        sizepielabel = 9
    ####
    IMGLABEL = [13, 14]
    for abrir, imglabel in zip([0, 0.5], IMGLABEL):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.pie(for_pie[1], colors = edge_colors[usercolormap][0:len(gos)])
        n = 0.9
        for i, j, k in zip(for_pie[0], for_pie[1], edge_colors[usercolormap][0:len(gos)]):
            ax.annotate(name_term[i]+'   ('+str(j)+')',
                        xy=(1.1, n),
                        xytext=(1.1, n),
                        url = url_for_go_uniprot_quickgo[i],
                        size=sizepielabel,
                        bbox=dict(boxstyle="round", alpha=0.5, fc=k, ec="k", lw=0.72,
                                 url = url_for_go_uniprot_quickgo[i]))
            n -= sizepielabel * .01 # una décima parte
        centre_circle = plt.Circle((0,0),abrir,fc='white', alpha = 1)
        plt.gca().add_artist(centre_circle)
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.3, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Circle_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Circle_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
                    
    ##############################################################################
    #>>>>>>>>>>    15 y 16
    ##############################################################################
    short_name_term = dict(zip(YYYYYYYYYY.base.tolist(), YYYYYYYYYY.Short_Term.tolist()))
    # kt = kegg tabla
    kt = XXXXXXXXXX[['GO', 'Entry']]
    df1 = kt.merge(kt, on = 'Entry', how = 'left').drop_duplicates()
    matrix = df1.pivot_table(values='Entry',index=['GO_x'],aggfunc=len,columns=['GO_y'])
    ###
    df_mat = []
    n = -1
    for i in list(matrix.columns.values):
        n += 1
        new = DataFrame(matrix.iloc[n:len(matrix)][i])
        nn = -1
        for index, row in new.iterrows():
            nn += 1
            df_mat.append([index, i, new.iloc[nn][i]])
        nn = 0
    ###
    df_mat = DataFrame(df_mat, columns = ['go0', 'go1', 'val']).dropna()
    ###
    nodos = []
    for index, row in df_mat.iterrows():
        if row.go0 == row.go1:
            #print(row.go0, row.go1)
            continue
        else:
            #print(row.go0, row.go1)
            nodos.append([row.go0, row.go1, row.val])
    nodos = DataFrame(nodos)
    if len(nodos) > 1:
        nodos = DataFrame([[i for i in nodos[0]], [i for i in nodos[1]], nodos[2]]).T
    else:
        pass
    #### >>>>>>>>>>>>>>>>
    # si interacciona con mas uno, eliminar la redundancia, y si no interacciona con ninguno, dejar el nodo
    # y su valor, este se verá en la red como un nodo aislado
    aislado = [i for i in matrix.columns if len(matrix[[i]].dropna()) == 1]
    aislado = [df_mat[df_mat.go0 == i] for i in aislado]
    if len(aislado) > 0:
        aislado = pd.concat(aislado)
        aislado.columns = [0, 1, 2]
        aislado = DataFrame([[i for i in aislado[0]], [i for i in aislado[1]], aislado[2]]).T
        nodos = pd.concat([nodos, aislado])
    else:
        pass
    g = nx.Graph()
    for index, row in nodos.iterrows():
        g.add_edge(row[0], row[1],weight = int(row[2]))
    ed = [(u,v,d['weight']) for (u,v,d) in g.edges(data=True) if d['weight'] >= 1]
    #------------------------------------------------------------
    arc_weight = nx.get_edge_attributes(g,'weight')
    NEWCOLOR = ['black', colorletra]
    IMGLABEL = [15, 16]
    for newcolor, imglabel, size_la in zip(NEWCOLOR, IMGLABEL, [sizepielabel * 0.35, sizepielabel * 0.35]):
        acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        pos = nx.kamada_kawai_layout(g, dist=None, weight='weight', scale=1, center=None, dim=2)
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(g,pos,node_list = labnodeterms,
                               node_color= [labnodeterms[i] for i in g.nodes()],
                               alpha= 1,
                               node_size = list(np.array(sizenodo) * 150),
                               zorder = 2)
        nx.draw_networkx_edges(g,pos, edgelist=ed,width = np.array([i[2] for i in ed]),
                                   alpha= 0.6,edge_color=  'grey',style='-')
        nx.draw_networkx_edge_labels(g, pos, edge_color= 'grey',
                                     font_size=size_la, edge_labels=arc_weight)
        for nod_term in list(g.nodes()):
            ax.annotate(short_name_term[nod_term],
                        xy=pos[nod_term], xycoords='data',
                        #url = url_for_kegg[nod_term], #rotation=45,
                        xytext=pos[nod_term],textcoords='data',
                        color= newcolor,
                        size=size_la,
                        ha='center', va="center",
                        bbox=dict(boxstyle="circle",
                                  pad=0, #url = url_for_kegg[nod_term]
                                  alpha=0.01, fc='whitesmoke',
                                  ec="none", ))
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes([0.5, 0.2, 0.5, 0.7])
        ejes = bar_parameters(df = frame3)
        plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
        plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True
        h = 0
        for i, j, k in zip(ejes[0] , ejes[1], cuentas_entry):
            # barras
            ax3.barh(i, j, height= 0.8,
                        color= labnodeterms[i],
                        align='center',
                        linewidth = 0,
                        alpha = 1)
            # valores
            ax3.annotate(' '+str(k),
                        xy= np.array([0 + j, h]), xycoords='data', #(rect.get_x() + rect.get_width() / 2, height),
                        xytext=np.array([0 + j, h]), textcoords='data',  # 3 points vertical offset
                        size=7, ha='left', va='center')
            ax3.annotate(i,
                        xy=np.array([-0.2, h]), xycoords='data',
                        url = url_for_go_uniprot_quickgo[i], color = col_font_annotate[i],
                        xytext=np.array([-0.2, h]), textcoords='data',
                        size=7, ha='right', va="center",# fontweight='bold',
                        bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[i],
                                  url = url_for_go_uniprot_quickgo[i], ec="none"))        
            h +=1
        ax3.plot(np.array(valores_constantes), np.array(list(range(0,20))),
                 color = 'white',linewidth=0.5, zorder=1)
        ax3.scatter(np.array(valores_constantes), np.array(list(range(0,20))),
                 s=5,c='white', marker='s', zorder=2)
        ax3.plot(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 color = 'blue',linewidth=0.5)
        ax3.scatter(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 s=5,c='blue', marker='o', zorder=2)
        plt.text(0, 21, "       "+title+"\n\nP-value & Ajusted P-value",size= 8,fontweight='bold')
        # configuracionmanual de la escala
        scala = list(range(0,300+1, 2)) # escala prdeterminada, independiente de los valores
        q=0
        w=2
        for i in range(len(scala)): # este bucle encuentra el valor maximo dentro de la escala predeterminada
            if q <= frame2.LogminP.max() <= w:
                val_max_to_scala = w
                break
            q+=2
            w+=2
        ax3.plot([0, val_max_to_scala], [19.8, 19.8], color = 'black',linewidth=0.3, zorder=1)
        for i in list(range(0, val_max_to_scala+1,2)):
            plt.text(i, 20.2, str(i), size= 6, ha='center')
            plt.text(i, 19.8, '|', size= 4, ha='center')
        if val_max_to_scala > 30:
            plt.xticks([-2.5] + [val_max_to_scala*1.5], size=6, color='black')
        else:
            plt.xticks([-2.5] + [val_max_to_scala*3], size=6, color='black')
        plt.yticks(color='none') # oculta las etiquetas del eje y
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
                        
    ##############################################################################
    #>>>>>>>>>>    17 y 18
    ##############################################################################
    arc_weight = nx.get_edge_attributes(g,'weight')
    NEWCOLOR = ['black', colorletra]
    IMGLABEL = [17, 18]
    for newcolor, imglabel, size_la in zip(NEWCOLOR, IMGLABEL, [sizepielabel * 0.35, sizepielabel * 0.35]):
        if imglabel == 18:
            acumulacion += str(imglabel)+'.'
        else: 
            acumulacion += str(imglabel)+', '
        sys.stdout.write("\rPlots: %s" % (acumulacion))   
        sys.stdout.flush()
        pos = nx.circular_layout(g)
        fig = plt.figure(figsize=(15, 7))
        ax = fig.add_axes([0, 0, .5, 1])
        nx.draw_networkx_nodes(g,pos,node_list = gos,
                               node_color= [labnodeterms[i] for i in g.nodes()],
                               alpha= 1,
                               node_size = list(np.array(sizenodo) * 150),
                               zorder = 2)
        nx.draw_networkx_edges(g,pos, edgelist=ed,width = np.array([i[2] for i in ed]),
                                   alpha= 0.6,edge_color=  'grey',style='-')
        nx.draw_networkx_edge_labels(g, pos, edge_color= 'grey',
                                     font_size=size_la, edge_labels=arc_weight)
        ax.axis('equal')
        for nod_term in list(g.nodes()):
            ax.annotate(short_name_term[nod_term],
                        xy=pos[nod_term], xycoords='data',
                        #url = url_for_kegg[nod_term], #rotation=45,
                        xytext=pos[nod_term],textcoords='data',
                        color= newcolor,
                        size=size_la,
                        ha='center', va="center",
                        bbox=dict(boxstyle="circle",
                                  pad=0, #url = url_for_kegg[nod_term]
                                  alpha=0.01, fc='whitesmoke',
                                  ec="none", ))
        ax.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        ax3 = fig.add_axes([0.5, 0.2, 0.5, 0.7])
        ejes = bar_parameters(df = frame3)
        plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
        plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True
        h = 0
        for i, j, k in zip(ejes[0] , ejes[1], cuentas_entry):
            # barras
            ax3.barh(i, j, height= 0.8,
                        color= labnodeterms[i],
                        align='center',
                        linewidth = 0,
                        alpha = 1)
            # valores
            ax3.annotate(' '+str(k),
                        xy= np.array([0 + j, h]), xycoords='data', #(rect.get_x() + rect.get_width() / 2, height),
                        xytext=np.array([0 + j, h]), textcoords='data',  # 3 points vertical offset
                        size=7, ha='left', va='center')
            ax3.annotate(i,
                        xy=np.array([-0.2, h]), xycoords='data',
                        url = url_for_go_uniprot_quickgo[i], color = col_font_annotate[i],
                        xytext=np.array([-0.2, h]), textcoords='data',
                        size=7, ha='right', va="center",# fontweight='bold',
                        bbox=dict(boxstyle="round", alpha=0.5, fc=labnodeterms[i],
                                  url = url_for_go_uniprot_quickgo[i], ec="none"))        
            h +=1
        ax3.plot(np.array(valores_constantes), np.array(list(range(0,20))),
                 color = 'white',linewidth=0.5, zorder=1)
        ax3.scatter(np.array(valores_constantes), np.array(list(range(0,20))),
                 s=5,c='white', marker='s', zorder=2)
        ax3.plot(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 color = 'blue',linewidth=0.5)
        ax3.scatter(np.array(logaritmo_fdr), np.array(list(range(0,20))),
                 s=5,c='blue', marker='o', zorder=2)
        plt.text(0, 21, "       "+title+"\n\nP-value & Ajusted P-value",size= 8,fontweight='bold')
        # configuracionmanual de la escala
        scala = list(range(0,300+1, 2)) # escala prdeterminada, independiente de los valores
        q=0
        w=2
        for i in range(len(scala)): # este bucle encuentra el valor maximo dentro de la escala predeterminada
            if q <= frame2.LogminP.max() <= w:
                val_max_to_scala = w
                break
            q+=2
            w+=2
        ax3.plot([0, val_max_to_scala], [19.8, 19.8], color = 'black',linewidth=0.3, zorder=1)
        for i in list(range(0, val_max_to_scala+1,2)):
            plt.text(i, 20.2, str(i), size= 6, ha='center')
            plt.text(i, 19.8, '|', size= 4, ha='center')
        if val_max_to_scala > 30:
            plt.xticks([-2.5] + [val_max_to_scala*1.5], size=6, color='black')
        else:
            plt.xticks([-2.5] + [val_max_to_scala*3], size=6, color='black')
        plt.yticks(color='none') # oculta las etiquetas del eje y
        ax3.axis('off')
        #■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
        captation = fig.add_axes([.39, 0, 0.11, 0.02])
        captation.text(0,0.3, 'NeVOmics {}'.format(datetime.now()).split('.')[0], size=7,ha='left',color= 'black')
        captation.axis('off')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.svg', bbox_inches='tight')
        plt.savefig(localizacion+'/NeVOmics_Plot_Network_'+str(imglabel)+'.png', dpi = 600, bbox_inches='tight')
        plt.close()
        
    return colorder





################ 
## UniProt
################
if anotacion_uniprot == '1':
    if createnetworks == '1':
        print('\n------------')
        print('Python Plots')
        if ('GO_BP' in list(go_tablas_uniprot.keys())) == True:
            print('Uniprot BP')
            if bpplots == '1':
                folder_uniprot_bp = 'Uniprot_plots/BP'
                os.makedirs(folder_uniprot_bp ,exist_ok=True)
                # crear directorio BP
                orden_colores_uni_bp = create_plots(XXXXXXXXXX = go_tablas_uniprot['GO_BP'],
                            YYYYYYYYYY = aprobados_uniprot['GO_BP'],
                            title = 'Biological Process',
                            localizacion = folder_uniprot_bp,
                            bar_title = barcolortitle)
            else:
                print('BP: No graphics were generated')
        else:
            print('There are no enriched terms for BP')
            pass
        if ('GO_MF' in list(go_tablas_uniprot.keys())) == True:
            print('\nUniprot MF')
            if mfplots == '1':
                folder_uniprot_mf = 'Uniprot_plots/MF'
                os.makedirs(folder_uniprot_mf ,exist_ok=True)
                # crear directorio MF
                orden_colores_uni_mf = create_plots(XXXXXXXXXX = go_tablas_uniprot['GO_MF'],
                            YYYYYYYYYY = aprobados_uniprot['GO_MF'],
                            title = 'Molecular Function',
                            localizacion = folder_uniprot_mf,
                            bar_title = barcolortitle)
            else:
                print('MF: No graphics were generated')
        else:
            print('There are no enriched terms for MF')
            pass
        if ('GO_CC' in list(go_tablas_uniprot.keys())) == True:
            print('\nUniprot CC')
            if ccplots == '1':
                folder_uniprot_cc = 'Uniprot_plots/CC'
                os.makedirs(folder_uniprot_cc ,exist_ok=True)
                # crear directorio CC
                orden_colores_uni_cc = create_plots(XXXXXXXXXX = go_tablas_uniprot['GO_CC'],
                            YYYYYYYYYY = aprobados_uniprot['GO_CC'],
                            title = 'Cellular Component',
                            localizacion = folder_uniprot_cc,
                            bar_title = barcolortitle)
            else:
                print('CC: No graphics were generated')
        else:
            print('There are no enriched terms for CC')
            pass
    ################ 
    ## GOA
    ################
if anotacion_goa == '1':
    if createnetworks == '1':
        print('\n------------')
        print('Python Plots')
        if ('GO_BP' in list(go_tablas_uniprot.keys())) == True:
            print('GOA BP')
            if bpplots == '1':
                folder_goa_bp = 'GOA_plots/BP'
                os.makedirs(folder_goa_bp ,exist_ok=True)
                # crear directorio BP
                orden_colores_goa_bp = create_plots(XXXXXXXXXX = go_tablas_goa['GO_BP'],
                            YYYYYYYYYY = aprobados_goa['GO_BP'],
                            title = 'Biological Process',
                            localizacion = folder_goa_bp,
                            bar_title = barcolortitle)
            else:
                print('BP: No graphics were generated')
        else:
            print('There are no enriched terms for BP')
            pass    
        if ('GO_MF' in list(go_tablas_uniprot.keys())) == True:
            print('\nGOA MF')
            if mfplots == '1':
                folder_goa_mf = 'GOA_plots/MF'
                os.makedirs(folder_goa_mf ,exist_ok=True)
                # crear directorio BP
                orden_colores_goa_mf = create_plots(XXXXXXXXXX = go_tablas_goa['GO_MF'],
                            YYYYYYYYYY = aprobados_goa['GO_MF'],
                            title = 'Molecular Function',
                            localizacion = folder_goa_mf,
                            bar_title = barcolortitle)
            else:
                print('MF: No graphics were generated')
        else:
            print('There are no enriched terms for MF')
            pass
        if ('GO_CC' in list(go_tablas_uniprot.keys())) == True:
            print('\nGOA CC')
            if ccplots == '1':
                folder_goa_cc = 'GOA_plots/CC'
                os.makedirs(folder_goa_cc ,exist_ok=True)
                # crear directorio BP
                orden_colores_goa_cc = create_plots(XXXXXXXXXX = go_tablas_goa['GO_CC'],
                            YYYYYYYYYY = aprobados_goa['GO_CC'],
                            title = 'Cellular Component',
                            localizacion = folder_goa_cc,
                            bar_title = barcolortitle)
            else:
                print('CC: No graphics were generated')
        else:
            print('There are no enriched terms for CC')
            pass






# Preparacion de colores para bar colormap en R, la informacion la obtengo del 
# diccionario creado preciamente llamado <font color = red>"sequentials_colors"<font>
# con este comando extraigo una lista de colores para la barra colormap en R, la defino desde python

color_for_bar_in_R = [matplotlib.colors.to_hex(i) for i in sequentials_colors[colormap_definido](np.linspace(0, 1, 50))]

colores_bar_R = DataFrame(color_for_bar_in_R, columns = ['bar_color_R'])

######################-----------------#####################
def create_plots_order_for_R(XXXXXXXXXX = DataFrame([]),
                 YYYYYYYYYY = DataFrame([])):
    matrix = XXXXXXXXXX.pivot_table(values='Entry',index=['label'],aggfunc=len,columns=['GO', 'Term', 'Short_Term'])
    df_mat = []
    for i in list(matrix.columns.values):
        new = DataFrame(matrix[i])
        for x, y in zip(list(new[i].index), list(new[i].values)):
            df_mat.append([x, i, y])
    df_mat = DataFrame(df_mat, columns = ['go0', 'go1', 'val']).dropna()
    nodos = []
    for index, row in df_mat.iterrows():
        if row.go0 == row.go1:
            #print(row.go0, row.go1)
            continue
        else:
            #print(row.go0, row.go1)
            nodos.append([row.go0, row.go1, row.val])
    nodos = DataFrame(nodos)
    nodos = DataFrame([[i for i in nodos[0]],
                       [i[0] for i in nodos[1]],
                        nodos[2]]).T
    G=nx.Graph()
    for index, row in nodos.iterrows():
        G.add_edge(str(row[0]), row[1],weight = row[2])
    #esmall=[(u,v,d['weight']) for (u,v,d) in G.edges(data=True) if d['weight'] > 0]
    xxx = []
    for i in G.nodes():
        xxx.append(str(i))
    yyy = DataFrame(xxx, columns = ['label'])
    # si hay columna de valores numéricos en el input
    if 'values' in list(list_input.select_dtypes('object').columns):
        zzz = yyy.merge(XXXXXXXXXX[['label', 'values']], on = 'label', how = 'left').drop_duplicates().reset_index(drop = True)
        zzz = zzz.sort_values(by ='values',ascending=False).reset_index(drop=True)
    else:
        zzz = yyy.merge(XXXXXXXXXX[['label']], on = 'label', how = 'left').drop_duplicates().reset_index(drop = True)
    G=nx.Graph()
    for index, row in nodos.iterrows():
        G.add_edge(str(row[0]), row[1],weight = row[2])
    #esmall=[(u,v,d['weight']) for (u,v,d) in G.edges(data=True) if d['weight'] > 0]
    xxx = []
    for i in G.nodes():
        xxx.append(str(i))
    yyy = DataFrame(xxx, columns = ['label'])
    zzz = yyy.merge(XXXXXXXXXX[['label', 'values']], on = 'label', how = 'left').drop_duplicates().reset_index(drop = True)
    zzz = zzz.sort_values(by ='values',ascending=False).reset_index(drop=True)
    ###################
    mycmap = sequentials_colors[colormap_definido].reversed()
    nulos = len(zzz['values']) - len(zzz['values'].dropna())
    null_col = list(np.repeat('', nulos))
    ids = list(np.round(np.linspace(zzz['values'].max(), zzz['values'].min(), len(zzz['values'])*4), 50))
    rangoforcolor = []
    valor_unico = []
    n = ids[0]
    for i in ids:
        if i == n:
            valor_unico.append(i)
            continue
        rangoforcolor.append([n, i])
        n = i
    #*******************************************************
    mycmap0 = mycmap(np.linspace(0, 1, len(rangoforcolor)))
    ##*********************************************************
    colores = []
    for i in mycmap0:
        colores.append(matplotlib.colors.to_hex(i))
    rangos = {}
    for k, j in zip(rangoforcolor, colores):
        if len(k) == 2:
            rangos[str(k[0])+','+str(k[1])] = j
        if len(k) == 1:
            rangos[str(k[0])] = j
    positivos = []
    for i in rangoforcolor:
        if len(i) == 2:
            for j in [np.round(x, 50) for x in zzz['values'] if x > 0]:
                if i[0] >= j >= i[1]:
                    #print(rangos[str(i[0])+','+str(i[1])],  j)
                    positivos.append(rangos[str(i[0])+','+str(i[1])])    
    negativos = []
    for i in rangoforcolor:
        if len(i) == 2:
            for j in [np.round(x, 50) for x in zzz['values'] if x < 0]:
                if i[0] >= j >= i[1]:
                    #print(rangos[str(i[0])+','+str(i[1])],  j)
                    negativos.append(rangos[str(i[0])+','+str(i[1])])   
    if len(valor_unico) > 1:
        zzz['cols'] = list(np.repeat(nodecolorsinback, len(zzz['values'].dropna()))) + null_col
    else:
        zzz['cols'] = positivos + negativos + null_col
        ######
    n = 0
    l = 10
    k = 15
    for i in range(10):
        if n+1 <= len(G.edges()) <= l:
            #print(k)
            valor = k
        #print(n+1, k, l)
        n += 10
        l += 10
        k -= 1
    if 101 <= len(G.edges()) <= 200:
        valor = 5
    if 201 <= len(G.edges()) <= 300:
        valor = 4
    if len(G.edges()) >= 301:
        valor = 3
    ####
    if hayvalores == 'nohayvalores':
        colorletra = nodecolorsinback
    else:
        colorletra = 'none'
    #################
    # asignacion de colores a cada entry, menos a terms
    colorder = dict(zip(zzz.label.tolist(), zzz.cols.tolist()))
    return colorder



def tablas_R(RRRRRRRRRR = DataFrame([]),
             YYYYYYYYYY = DataFrame([]),
             dictcolors = {},
             newnamecolumn = '',
             localizacionRscript = '',
             fdrv = 0):
    # agrego los colores de los genes/proteinas para que en R sea leida y los colores ya esten definidos
    colores_entry = []
    for i in RRRRRRRRRR.label:
        colores_entry.append(dictcolors[i])
    RRRRRRRRRR['entry_colors'] = colores_entry

    # agrego el titulo elegido por el usuario
    anex_bartitle = DataFrame([barcolortitle], columns = ['bar_title'])

    # preparacion del archivo de nodos
    edges_file_name = 'for_R_edges_GO_Enrich_Analysis_'+''.join(method_P)+'_'+str(fdrv)+'.csv'
    edges_frame = RRRRRRRRRR[['GO','Entry','Term', 'values', 'entry_colors']].drop_duplicates()

    if hayvalores == 'sihay':
        # agregar en el archivo edges la rampa de colores para R
        edges_frame = pd.concat([edges_frame,colores_bar_R], axis=1)
        edges_frame = pd.concat([edges_frame,anex_bartitle], axis=1)
    if hayvalores == 'nohayvalores':
        # agregar en el archivo edges una columna de colores unicos definicos como "nodecolorsinback" 
        edges_frame['bar_color_R'] = nodecolorsinback
        edges_frame = pd.concat([edges_frame,anex_bartitle], axis=1)
    edges_frame = edges_frame.rename(columns={'GO':newnamecolumn})
    edges_frame.to_csv(localizacionRscript+'/'+edges_file_name,index=None)

    gos = YYYYYYYYYY.base.drop_duplicates().tolist()
    labnodeterms = dict(zip(gos, edge_colors[usercolormap][0:len(gos)]))
    # agrego los colores de los terminos a la tabla para que en R sea leida y los colores ya esten definidos
    YYYYYYYYYY['term_colors'] = list(labnodeterms.values())

    nodes_file_name='for_R_nodes_GO_Enrich_Analysis_'+''.join(method_P)+'_'+str(fdrv)+'.csv'
    YYYYYYYYYY.drop_duplicates().to_csv(localizacionRscript+'/'+nodes_file_name,index=None)





# funcion para descargar el R script y modificar la localización de la librería
def get_GO_Rplots(location = ''):
    R_exe = open('../NeVOmics_locRexe.txt', 'r')
    R_exe = R_exe.read()
    ##
    R_lib = open('../NeVOmics_locRlib.txt', 'r')
    R_lib = R_lib.read()
    r_script = requests.get('https://raw.githubusercontent.com/bioinfproject/bioinfo/master/Folder/PlotsGO.R').content.decode()
    R_script_enrich = re.sub('rliblocation', R_lib, r_script)
    fr = open(location,'w')
    fr.write(R_script_enrich)
    fr.close()
def run_R_exe(move = '', Rscript = ''): # funcion para moverse a un directorio especifico, y ejecutar el R script
    R_exe = open('../NeVOmics_locRexe.txt', 'r')
    R_exe = R_exe.read()
    os.chdir(move)
    run_uni = subprocess.Popen([R_exe, 'CMD', 'BATCH', '--no-save', Rscript])
    run_uni.wait()
    os.chdir('../../')
    


# # Creación de Circos en R para cada una de las bases de datos



################
###   UniProt
################
if anotacion_uniprot == '1':
    if createcircos == '1':
        print('\n\n-----------------------')
        print('Building graphics with R ...')
        print('Wait...')
        if ('GO_BP' in list(go_tablas_uniprot.keys())) == True:
            print('Uniprot BP')
            if bpplots == '1':
                folder_uniprot_bp = 'Uniprot_plots/BP'
                os.makedirs(folder_uniprot_bp ,exist_ok=True)
                ### descargar PlotsGO.R y mandarlo al directorio para graficos
                get_GO_Rplots(location = 'Uniprot_plots/BP/GO_Enrichment_Plots.R')
                ###
                os.makedirs('Uniprot_plots/BP/R_GO_plots', exist_ok=True)
                # crear directorio BP
                orden_colores_uni_bp = create_plots_order_for_R(XXXXXXXXXX = go_tablas_uniprot['GO_BP'],
                            YYYYYYYYYY = aprobados_uniprot['GO_BP'])

                tablas_R(RRRRRRRRRR = go_tablas_uniprot['GO_BP'],
                         YYYYYYYYYY = aprobados_uniprot['GO_BP'],
                        dictcolors = orden_colores_uni_bp,
                        newnamecolumn = 'GObp',
                        localizacionRscript = folder_uniprot_bp,
                        fdrv = fdrs[0])
                ######
                run_R_exe(move = 'Uniprot_plots/BP', Rscript = 'GO_Enrichment_Plots.R')
            else:
                print('BP: No graphics were generated')
        else:
            print('There are no enriched terms for BP')
            pass
        #-----------------------------------------------------------------------------
        if ('GO_MF' in list(go_tablas_uniprot.keys())) == True:
            print('Uniprot MF')
            if mfplots == '1':
                folder_uniprot_mf = 'Uniprot_plots/MF'
                os.makedirs(folder_uniprot_mf ,exist_ok=True)
                ### descargar PlotsGO.R y mandarlo al directorio para graficos
                get_GO_Rplots(location = 'Uniprot_plots/MF/GO_Enrichment_Plots.R')
                ###
                os.makedirs('Uniprot_plots/MF/R_GO_plots', exist_ok=True)
                # crear directorio BP
                orden_colores_uni_mf = create_plots_order_for_R(XXXXXXXXXX = go_tablas_uniprot['GO_MF'],
                            YYYYYYYYYY = aprobados_uniprot['GO_MF'])

                tablas_R(RRRRRRRRRR = go_tablas_uniprot['GO_MF'],
                        YYYYYYYYYY = aprobados_uniprot['GO_MF'],
                        dictcolors = orden_colores_uni_mf,
                        newnamecolumn = 'GOmf',
                        localizacionRscript = folder_uniprot_mf,
                        fdrv = fdrs[1])
                ######
                run_R_exe(move = 'Uniprot_plots/MF', Rscript = 'GO_Enrichment_Plots.R')
            else:
                print('MF: No graphics were generated')
        else:
            print('There are no enriched terms for MF')
            pass
        #-----------------------------------------------------------------------------
        if ('GO_CC' in list(go_tablas_uniprot.keys())) == True:
            print('Uniprot CC')
            if ccplots == '1':
                folder_uniprot_cc = 'Uniprot_plots/CC'
                os.makedirs(folder_uniprot_cc ,exist_ok=True)
                ### descargar PlotsGO.R y mandarlo al directorio para graficos
                get_GO_Rplots(location = 'Uniprot_plots/CC/GO_Enrichment_Plots.R')
                ###
                os.makedirs('Uniprot_plots/CC/R_GO_plots', exist_ok=True)
                # crear directorio BP
                orden_colores_uni_cc = create_plots_order_for_R(XXXXXXXXXX = go_tablas_uniprot['GO_CC'],
                            YYYYYYYYYY = aprobados_uniprot['GO_CC'])

                tablas_R(RRRRRRRRRR = go_tablas_uniprot['GO_CC'],
                        YYYYYYYYYY = aprobados_uniprot['GO_CC'],
                        dictcolors = orden_colores_uni_cc,
                        newnamecolumn = 'GOcc',
                        localizacionRscript = folder_uniprot_cc,
                        fdrv = fdrs[2])
                ######
                run_R_exe(move = 'Uniprot_plots/CC', Rscript = 'GO_Enrichment_Plots.R')
            else:
                print('CC: No graphics were generated')
        else:
            print('There are no enriched terms for CC')
            pass
        #-----------------------------------------------------------------------------
################
###   GOA
################
if anotacion_goa == '1':
    if createcircos == '1':
        print('\n\n-----------------------')
        print('Building graphics with R ...')
        print('Wait...')
        if ('GO_BP' in list(go_tablas_uniprot.keys())) == True:
            print('GOA BP')
            if bpplots == '1':
                folder_goa_bp = 'GOA_plots/BP'
                os.makedirs(folder_goa_bp ,exist_ok=True)
                ### descargar PlotsGO.R y mandarlo al directorio para graficos
                get_GO_Rplots(location = 'GOA_plots/BP/GO_Enrichment_Plots.R')
                ###
                os.makedirs('GOA_plots/BP/R_GO_plots', exist_ok=True)
                # crear directorio BP
                orden_colores_goa_bp = create_plots_order_for_R(XXXXXXXXXX = go_tablas_goa['GO_BP'],
                            YYYYYYYYYY = aprobados_goa['GO_BP'])

                tablas_R(RRRRRRRRRR = go_tablas_goa['GO_BP'],
                        YYYYYYYYYY = aprobados_goa['GO_BP'],
                        dictcolors = orden_colores_goa_bp,
                        newnamecolumn = 'GObp',
                        localizacionRscript = folder_goa_bp,
                        fdrv = fdrs[0])
                ######
                run_R_exe(move = 'GOA_plots/BP', Rscript = 'GO_Enrichment_Plots.R')
            else:
                print('BP: No graphics were generated')
        else:
            print('There are no enriched terms for BP')
            pass
        #-----------------------------------------------------------------------------
        if ('GO_MF' in list(go_tablas_goa.keys())) == True:
            print('GOA MF')
            if mfplots == '1':
                folder_goa_mf = 'GOA_plots/MF'
                os.makedirs(folder_goa_mf ,exist_ok=True)
                ### descargar PlotsGO.R y mandarlo al directorio para graficos
                get_GO_Rplots(location = 'GOA_plots/MF/GO_Enrichment_Plots.R')
                ###
                os.makedirs('GOA_plots/MF/R_GO_plots', exist_ok=True)
                # crear directorio BP
                orden_colores_goa_mf = create_plots_order_for_R(XXXXXXXXXX = go_tablas_goa['GO_MF'],
                            YYYYYYYYYY = aprobados_goa['GO_MF'])

                tablas_R(RRRRRRRRRR = go_tablas_goa['GO_MF'],
                        YYYYYYYYYY = aprobados_goa['GO_MF'],
                        dictcolors = orden_colores_goa_mf,
                        newnamecolumn = 'GOmf',
                        localizacionRscript = folder_goa_mf,
                        fdrv = fdrs[1])
                ######
                run_R_exe(move = 'GOA_plots/MF', Rscript = 'GO_Enrichment_Plots.R')
            else:
                print('MF: No graphics were generated')
        else:
            print('There are no enriched terms for MF')
            pass
        #-----------------------------------------------------------------------------
        if ('GO_CC' in list(go_tablas_goa.keys())) == True:
            print('GOA CC')
            if ccplots == '1':
                folder_goa_cc = 'GOA_plots/CC'
                os.makedirs(folder_goa_cc ,exist_ok=True)
                ### descargar PlotsGO.R y mandarlo al directorio para graficos
                get_GO_Rplots(location = 'GOA_plots/CC/GO_Enrichment_Plots.R')
                ###
                os.makedirs('GOA_plots/CC/R_GO_plots', exist_ok=True)
                # crear directorio BP
                orden_colores_goa_cc = create_plots_order_for_R(XXXXXXXXXX = go_tablas_goa['GO_CC'],
                            YYYYYYYYYY = aprobados_goa['GO_CC'])

                tablas_R(RRRRRRRRRR = go_tablas_goa['GO_CC'],
                        YYYYYYYYYY = aprobados_goa['GO_CC'],
                        dictcolors = orden_colores_goa_cc,
                        newnamecolumn = 'GOcc',
                        localizacionRscript = folder_goa_cc,
                        fdrv = fdrs[2])
                ######
                run_R_exe(move = 'GOA_plots/CC', Rscript = 'GO_Enrichment_Plots.R')
            else:
                print('CC: No graphics were generated')
        else:
            print('There are no enriched terms for CC')
            pass

#del_stop_process()

