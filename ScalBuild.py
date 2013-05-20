import sublime, sublime_plugin
import glob
import os
from xml.etree.ElementTree import ElementTree

#from ScalBuild import DataListener

import ScalBuild.Exec2
from ScalBuild.Exec2 import DataListener


def getProjectsScalaFolders():

    resFolders = []

    ## Get All Folders:
    #############
    for folder in sublime.active_window().folders():

        ## Check if the folder may be sbt buildable
        ##############

        ## Pattern src/main/scala is present
        detectionPatterns = ['src/main/scala','src-main-scala','*.scala']
        foundScala = False
        for pattern in detectionPatterns:
            if len(glob.glob(folder+"/"+pattern))!=0 :
                resFolders.append(folder)
                break

    return resFolders



'''
This Class Describes a project, with informations about it, and dependencies etc...
'''
class ScalBuildProject(object):

    def printlnToOutput(self,string):
        if self.dataListener:
            self.dataListener.println(string)
        else:
            print(string)

    def __init__(self, projectPath=None):

        ## Default Project IDs
        ################
        self.artifactId  = os.path.basename(projectPath)
        self.groupId     = os.path.basename(projectPath)
        self.version     = "unknown"
        self.projectPath = projectPath
        self.dependencies = []

        ## Maven project ?
        #####################
        if os.path.isfile(projectPath+"/pom.xml"):

            self.buildSystem = "maven"

            ## Read in XML
            doc = ElementTree(file=projectPath+"/pom.xml")

            #print("IN MAVEN PROJECT (folder "+self.artifactId+")")

            #### Update Project infos
            ###################

            ## Parent Infos
            parentElement = doc.find("{http://maven.apache.org/POM/4.0.0}parent")
            if parentElement:
                self.parent = {
                            "artifactId":parentElement.findtext('{http://maven.apache.org/POM/4.0.0}artifactId'),
                            "groupId": parentElement.findtext('{http://maven.apache.org/POM/4.0.0}groupId'),
                            "version": parentElement.findtext('{http://maven.apache.org/POM/4.0.0}version')
                        }

            ## Local Infos
            self.artifactId  = doc.findtext('{http://maven.apache.org/POM/4.0.0}artifactId')
            self.groupId     = doc.findtext('{http://maven.apache.org/POM/4.0.0}groupId')
            self.version     = doc.findtext('{http://maven.apache.org/POM/4.0.0}version')

            #### Get Dependencies with XPATh
            ####################
            dependencyElements = doc.findall("{{{0}}}dependencies/{{{0}}}dependency".format("http://maven.apache.org/POM/4.0.0"))
            for dependency in dependencyElements:
                #print("Found Dependency: "+str(dependency))
                self.dependencies += [{
                            "artifactId":dependency.findtext('{http://maven.apache.org/POM/4.0.0}artifactId'),
                            "groupId": dependency.findtext('{http://maven.apache.org/POM/4.0.0}groupId'),
                            "version": dependency.findtext('{http://maven.apache.org/POM/4.0.0}version')
                        }]
        else:
            self.buildSystem = "sbt"
        ## Report
        ################
        #for dep in dependencies


    ## Build The Project using maven of SBT or whatever
    ##############################
    def build(self):

        if self.buildSystem == "sbt":

            self.printlnToOutput("[Project] Building Using sbt")

            ## Change output parameters
            ###############################
            self.dataListener.setOutputSetting("result_base_dir", self.projectPath)
            self.dataListener.setOutputSetting("result_file_regex", "^\[error\] (.+):([0-9]+): (.+)$")

            ## Create Executor
            ############################
            executor = ScalBuild.Exec2.CommandExecutor(self.dataListener)
         

            ## Build
            ################
            executor.run( shell_cmd = "cd "+self.projectPath+" && sbt compile",
                encoding =  "UTF-8" )

        elif self.buildSystem == "maven":

            self.printlnToOutput("[Project] Building Using maven")

            ## Change output parameters
            ###############################
            self.dataListener.setOutputSetting("result_base_dir", self.projectPath)
            self.dataListener.setOutputSetting("result_file_regex", "^\[error\] (.+):([0-9]+): (.+)$")

            ## Create Executor
            ############################
            executor = ScalBuild.Exec2.CommandExecutor(self.dataListener)

            ## Build
            ################
            executor.run( shell_cmd = "cd "+self.projectPath+" && mvn compile",
                encoding =  "UTF-8" )

        else:
            self.printlnToOutput("[Project] Unsupported buildSystem")


    ## Returns String id (groupId:artifactId:version)
    def strId(self):
        return self.groupId+":"+self.artifactId+":"+self.version

class ScalBuildCommand(sublime_plugin.WindowCommand,DataListener):

    def description(self):
        return "Build"

    ## Data Listener Implementation
    def on_data(self,string):
        self.outputPanel.run_command('append', {'characters':string, 'force': True, 'scroll_to_end': True})

    ## Utility println
    def printlnToOutput(self,string):
        self.outputPanel.run_command('append', {'characters':string+"\n", 'force': True, 'scroll_to_end': True})

    ## Change output view settings
    def setOutputSetting(self,name,value):
        self.outputPanel.settings().set(name, value)

    ## Main Run of command
    ###########################
    def run(self,paths = []):

        ## Prepare Output Panel,
        ## Use "exec", so that output gets shared with the normal exec command call
        ############################################

        self.outputPanel = self.window.create_output_panel("exec")
        self.outputPanel.set_name("exec")


        ## Output Customisation
        #############################
        self.outputPanel.settings().set("line_numbers", False)
        self.outputPanel.settings().set("gutter", False)
        self.outputPanel.settings().set("scroll_past_end", False)
        self.window.run_command("show_panel", {"panel": "output.exec"})

        self.printlnToOutput("Call args: "+str(paths))

        ## Limit Build to project of current view or provided comand paths
        ##################################
        currentFile = self.window.active_view().file_name()
        if len(paths) > 0:
            currentFile = paths[0]

        if currentFile != None:
            self.printlnToOutput("Current View: "+currentFile)
        else:
            self.printlnToOutput("Current View is not defined: ")




        ## Find Project To be build
        ##################
        buildProjects = []



        ## Find Projects To be build
        ###############
        self.printlnToOutput("Building Scala Projects from Project's Folders")
        for scalaFolder in getProjectsScalaFolders():

            self.printlnToOutput("-----------------------------------------")
            self.printlnToOutput("Scala Project Folder: "+scalaFolder)
            self.printlnToOutput("Panel: "+str(self.outputPanel))

            ## Parse Maven Project to get infos
            ###################
            project = ScalBuildProject(scalaFolder)
            project.dataListener = self

            ### Show Infos
            self.printlnToOutput("- artifactId: "+project.artifactId)
            self.printlnToOutput("- groupId: "+project.groupId)
            self.printlnToOutput("- version: "+project.version)


            #### Show Dependencies
            #self.printlnToOutput("---> Dependencies: "+str(project.dependencies))
            for dep in project.dependencies:
                self.printlnToOutput("---> Dependency: "+dep["artifactId"])


            ## Is Current File in Project ?
            ## It no current File -> add all projects to build
            ########################
            if currentFile == None:
                buildProjects.append(project)
            elif currentFile != None and currentFile.startswith(project.projectPath):
                buildProjects.append(project)


        ## Build Selected Projects
        #######################
        self.printlnToOutput("--- Building Projects ----")
        for project in buildProjects:
            self.printlnToOutput("Project: "+project.strId())
            project.build()

        ## Detect For each folder the project, and dependencies
        ####################

        ## Reorder Projects to have dependencies newly build first
        ###############



class ScalProjectStatusCommand(sublime_plugin.ApplicationCommand):

    def printlnToOutput(self,string):
        self.outputPanel.run_command('append', {'characters':string+"\n", 'force': True, 'scroll_to_end': True})

    def run(self):

        ## Prepare Output Panel,
        ## Use "exec", so that output gets shared with the normal exec command call
        ############################################

        self.outputPanel = self.window.create_output_panel("exec")
        self.outputPanel.set_name("exec")
        self.window.run_command("show_panel", {"panel": "output.exec"})



        ## Find Project To be build
        ##################
        self.printlnToOutput("Building Scala Projects from Project's Folders")
        for scalaFolder in getProjectsScalaFolders():

            self.printlnToOutput("-----------------------------------------")
            self.printlnToOutput("Scala Project Folder: "+scalaFolder)
            self.printlnToOutput("Panel: "+str(self.outputPanel))

            ## Parse Maven Project to get infos
            ###################
            project = ScalBuildProject(scalaFolder)

            ### Show Infos
            self.printlnToOutput("- artifactId: "+project.artifactId)
            self.printlnToOutput("- groupId: "+project.groupId)
            self.printlnToOutput("- version: "+project.version)


            #### Show Dependencies
            #self.printlnToOutput("---> Dependencies: "+str(project.dependencies))
            for dep in project.dependencies:
                self.printlnToOutput("---> Dependency: "+dep["artifactId"])

            ## Maven or Scala ?
            ##################

            ## Maven
            if os.path.isfile(scalaFolder+"/pom.xml"):
                self.printlnToOutput("---> Using maven to compile")

            ## Scala
            else:
                 self.printlnToOutput("---> Using sbt to compile")

            ## Execute scala
            '''
            sublime.active_window().run_command('exec2',
                                    {
                                        "shell_cmd": "cd "+scalaFolder+" && sbt compile",
                                        "encoding" : "UTF-8",
                                        "file_regex": "^\[error\] (.+):([0-9]+): (.+)$",
                                        "existingOutput" : self.outputPanel
                                    })
            '''

        ## Detect For each folder the project, and dependencies
        ####################

        ## Reorder Projects to have dependencies newly build first
        ###############



class ScalaProjectStatusFillBufferCommand(sublime_plugin.TextCommand):


    def run(self,edit):

        ## Write Hello
        ###############
        position = 0
        position += self.view.insert(edit,position,"Detected Scala Projects in this project, and SBT build status\n\n")

        ## Get All Folders:
        #############
        for folder in sublime.active_window().folders():

            ## Check if the folder may be sbt buildable
            ##############

            ## Pattern src/main/scala is present
            detectionPatterns = ['src/main/scala','src-main-scala','*.scala']
            foundScala = False
            for pattern in detectionPatterns:
                if len(glob.glob(folder+"/"+pattern))!=0 :
                    foundScala = True
                    break

            ## Print folder Name if scala detected
            ##########
            if foundScala:
                position += self.view.insert(edit,position,"Scala Folder: "+folder+"\n\n")




