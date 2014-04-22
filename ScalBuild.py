'''
  %%
  Copyright (C) 2008 - 2014 OSI / Computer Architecture Group @ Uni. Heidelberg
  %%
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as
  published by the Free Software Foundation, either version 3 of the
  License, or (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public
  License along with this program.  If not, see
  <http://www.gnu.org/licenses/gpl-3.0.html>.
  #L%
'''
import sublime, sublime_plugin
import glob
import os
from xml.etree.ElementTree import ElementTree

#from ScalBuild import DataListener

import ScalBuild.Exec2
from ScalBuild.Exec2 import DataListener

import ScalBuild.ScalProject
from ScalBuild.ScalProject import ScalBuildProject

import re

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


    ## Threaded Run
    ##########################
    def run(self,paths = [],buildTarget="install",rebuild=False):

        self.paths = paths
        self.buildTarget = buildTarget
        self.rebuild = rebuild


        sublime.set_timeout_async(self.do_run, 0)

    ## Main Run of command
    ###########################
    def do_run(self):

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
        self.outputPanel.set_syntax_file("Packages/ScalBuild/MavenOutput.tmLanguage")
        self.outputPanel.settings().set("color_scheme", "Packages/ScalBuild/MavenOutput.tmTheme")
        self.window.run_command("show_panel", {"panel": "output.exec"})

        self.printlnToOutput("Call args: "+str(self.paths))

        ## Limit Build to project of current view or provided comand paths
        ##################################
        currentFile = self.window.active_view().file_name()
        if len(self.paths) > 0:
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
                self.printlnToOutput("---> Project Selected for build:")
                ScalBuild.buildProjects.append(project)
            elif currentFile != None and currentFile.startswith(project.projectPath):
                self.printlnToOutput("---> Project Selected for build:")
                ScalBuild.buildProjects.append(project)

        ## Build Selected Projects
        #######################
        self.printlnToOutput("------ Building Projects --------")
        for project in ScalBuild.buildProjects:
            self.printlnToOutput("Project: "+project.strId())
            project.build(buildTarget=self.buildTarget,rebuild=self.rebuild)



#######################################
## This command just reloads the list of projects
########################################
class ScalReloadProjectsCommand(sublime_plugin.WindowCommand):

    def run(self):
        scalBuildListProjects()




###################################
## Command To Run a main file
######################################
class ScalRunMainCommand(sublime_plugin.WindowCommand,DataListener):

    def __init__(self, projectPath=None):

        ## Defaults
        self.lastMain    = None
        self.lastProject = None



    def description(self):
        return "Run Main using Scala over maven"

    ## Data Listener Implementation
    def on_data(self,string):

        #self.printlnToOutput("** Filtering **")

        self.outputPanel.run_command('append', {'characters':string, 'force': True, 'scroll_to_end': True})
        self.outputPanel.run_command('move_to',{'to': 'eof'})


        return
        ## Filter Out Escape Color characters
        #############
        ignoreNextCount = 0
        for x in string:
            #print("Character: "+x+" // "+str(ord(x)))

            if ignoreNextCount>0:
                ignoreNextCount-=1
            elif ord(x) == 27:
                #self.printlnToOutput("** found ESC **")
                #self.outputPanel.run_command('append', {'characters':"<b>", 'force': True, 'scroll_to_end': True})
                ignoreNextCount = 3
            else:
                ignoreNextCount = 0
                self.outputPanel.run_command('append', {'characters':x, 'force': True, 'scroll_to_end': True})


        #self.outputPanel.run_command('append', {'characters':"</b>", 'force': True, 'scroll_to_end': True})

        self.outputPanel.run_command('move_to',{'to': 'eof'})


    ## Utility println
    def printlnToOutput(self,string):
        self.outputPanel.run_command('append', {'characters':string+"\n", 'force': True, 'scroll_to_end': True})
        self.outputPanel.run_command('move_to',{'to': 'eof'})


    def run(self,paths=[],reRun=False):


        ## Open Output Panel
        ##################
        self.outputPanel = sublime.active_window().create_output_panel("run")
        self.outputPanel.set_syntax_file("Packages/ScalBuild/MavenOutput.tmLanguage")
        self.outputPanel.settings().set("color_scheme", "Packages/ScalBuild/MavenOutput.tmTheme")
        self.outputPanel.settings().set("result_file_regex", "^\[(?:(?i)ERROR|WARNING)\] (.+):([0-9]+): (.+)$")
        sublime.active_window().run_command("show_panel", {"panel": "output.run"})

        ## Run ?
        ##########################################

        ## Determine File and class
        #################
        if len(paths)==0 :
            currentFile = sublime.active_window().active_view().file_name()
        else :
            currentFile = paths[0]
        #currentFile = sublime.active_window().active_view().file_name()
        #currentFile = SideBarSelection(paths).getSelectedItems().index(0)


        #### Don't run not scala files
        if len(currentFile)>0 and currentFile.endswith(".scala")!=True :
            return

        self.printlnToOutput("Running File: "+currentFile)

        ## Determine Project Folder
        ##############
        currentProject = None
        for project in ScalBuild.availableProjects:
            if  currentFile.startswith(project.projectPath):
                currentProject = project
                break

        if currentProject==None:
            self.printlnToOutput("Error: File must be in a ScalBuild project folder ")
            return


        #### Determine Theoretical Class by extracting package and taking file name
        ################

        ## File Name
        fileName = re.search(".*/(.+)\.scala",currentFile)
        if fileName == None:
            self.printlnToOutput("Could not determine File name")
        else:
            fileName = fileName.group(1)

        ## Package
        f = open(currentFile)
        content = f.read()
        packageName = re.search("package\s+(.*)\s*;?\n\r?",content)
        if packageName == None:
            self.printlnToOutput("Could not determine packageName name")
        else:
            packageName = packageName.group(1)

        className = ""+packageName+"."+fileName

        #### Try to find scala Test markers
        ########################
        self.scalaTest = False
        scalaTestSearchRe = re.compile(r"^\s*class\s+"+fileName+r"\s+.*extends\s+[A-Za-z]+(?:Spec|Suite)\s+.*$",re.MULTILINE)
        #self.printlnToOutput("Searching with: "+scalaTestSearchRe.pattern)
        scalaSearch = scalaTestSearchRe.search(content)
        if scalaSearch != None:
            self.scalaTest = True

        ## Save run
        ####################
        self.lastMain = className
        self.lastProject = currentProject

        ## Run
        ###########
        self.printlnToOutput("Running main: "+self.lastMain)

        #### Run over maven
        executor = ScalBuild.Exec2.CommandExecutor(self)
        if self.scalaTest == True:
            self.printlnToOutput("Running as Scala Test ")
            executor.run( shell_cmd = "cd "+self.lastProject.projectPath+" && mvn test -Dsuites="+self.lastMain,
                encoding =  "UTF-8" )
        else:
            executor.run( shell_cmd = "cd "+self.lastProject.projectPath+" && mvn scala:run -q -Dmaven.test.skip=true -DmainClass="+self.lastMain,
                encoding =  "UTF-8" )








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


    def on_query_completions(self, view, prefix, locations):
        pass

