import sublime, sublime_plugin
import glob
import os
from xml.etree.ElementTree import ElementTree

#from ScalBuild import DataListener

import ScalBuild.Exec2
from ScalBuild.Exec2 import DataListener

import ScalBuild.ScalProject
from ScalBuild.ScalProject import ScalBuildProject


'''
    The ScalBuild Plugin maintains a list of description of detected Scala Projects

'''

# All the available projects
availableProjects = []

# The Projects to build during a build
buildProjects = []


'''
This Method lists all the scala projects, and merges in to the availableProjects list
'''
def scalBuildListProjects():

    print("Relisting projects: ")

    ## Clean
    ScalBuild.availableProjects = []

    ## Get All Folders
    #############
    windows = sublime.windows()
    for window in windows:
        for folder in window.folders():

            ## Check if the folder may be sbt buildable
            ##############

            ## Pattern src/main/scala is present
            detectionPatterns = ['src/main/scala','src-main-scala','*.scala']
            foundScala = False
            for pattern in detectionPatterns:
                if len(glob.glob(folder+"/"+pattern))!=0 :

                    ## Found Scala Project
                    #######################
                    print("Found Scala Project @"+folder)

                    ScalBuild.availableProjects.append(ScalBuildProject(folder))

                    break


# List Projects
scalBuildListProjects()


'''
This methods looks for a ScalBuildProject responding to the provided groupId artifactId and version in the availableProjects array
'''
def scalBuildGetProject(groupId,artifactId,version):

    for project in ScalBuild.availableProjects:
        if project.groupId==groupId and project.artifactId == artifactId and project.version == version:
            return project
    return None





############################################################

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





## This is the command that builds the projects
#########################################################


class ScalBuildCommand(sublime_plugin.WindowCommand,DataListener):

    def description(self):
        return "Build"

    ## Data Listener Implementation
    def on_data(self,string):
        self.outputPanel.run_command('append', {'characters':string, 'force': True, 'scroll_to_end': True})
        self.outputPanel.run_command('move_to',{'to': 'eof'})

    ## Utility println
    def printlnToOutput(self,string):
        self.outputPanel.run_command('append', {'characters':string+"\n", 'force': True, 'scroll_to_end': True})
        self.outputPanel.run_command('move_to',{'to': 'eof'})

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
        self.outputPanel.settings().set("gutter", True)
        self.outputPanel.settings().set("scroll_past_end", False)
        self.outputPanel.set_read_only(True)
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
        ScalBuild.buildProjects = []


        ## Find Projects To be build
        ###############
        self.printlnToOutput("Building Scala Projects from Available Projects")
        for project in ScalBuild.availableProjects:

            self.printlnToOutput("-----------------------------------------")
            self.printlnToOutput("Scala Project Folder: "+project.projectPath)
            self.printlnToOutput("Panel: "+str(self.outputPanel))

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
                ScalBuild.buildProjects.append(project)
            elif currentFile != None and currentFile.startswith(project.projectPath):
                ScalBuild.buildProjects.append(project)

        ## Build Selected Projects
        #######################
        self.printlnToOutput("------ Building Projects --------")
        for project in ScalBuild.buildProjects:
            self.printlnToOutput("Project: "+project.strId())
            project.build()




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



#################################
## Event Listener to detect changes in projects to be build
##################################
class ScalEventListener(sublime_plugin.EventListener):

    ## If File Belongs to a ScalaProject, request build
    ######################
    def on_post_save_async(self,view):
        print("Saved file: "+view.file_name())

        ## Do Saved file belon to a project?
        #########
        for project in ScalBuild.availableProjects:
            if view.file_name().startswith(project.projectPath):
                project.buildRequired = True



