import sublime, sublime_plugin
import glob
import os
from xml.etree.ElementTree import ElementTree



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
class ScalBuildProject():

    dependencies = []

    def __init__(self, projectPath=None):

        ## Default Project IDs
        ################
        self.artifactId  = os.path.basename(projectPath)
        self.groupId     = os.path.basename(projectPath)
        self.version     = "unknown"

        ## Maven project ?
        #####################
        if os.path.isfile(projectPath+"/pom.xml"):

            ## Read in XML
            doc = ElementTree(file=projectPath+"/pom.xml")

            print("IN MAVEN PROJECT (folder "+self.artifactId+")")

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
                print("Found Dependency: "+str(dependency))
                self.dependencies += [{
                            "artifactId":dependency.findtext('{http://maven.apache.org/POM/4.0.0}artifactId'),
                            "groupId": dependency.findtext('{http://maven.apache.org/POM/4.0.0}groupId'),
                            "version": dependency.findtext('{http://maven.apache.org/POM/4.0.0}version')
                        }]

        ## Report
        ################
        #for dep in dependencies




exec2_existing_output = 0

class ScalBuildCommand(sublime_plugin.WindowCommand):

    def printlnToOutput(self,string):
        self.outputPanel.run_command('append', {'characters':string+"\n", 'force': True, 'scroll_to_end': True})

    def run(self):

        ## Prepare Output Panel,
        ## Use "exec", so that output gets shared with the normal exec command call
        ############################################

        self.outputPanel = self.window.create_output_panel("exec")
        self.outputPanel.set_name("exec")
        self.window.run_command("show_panel", {"panel": "output.exec"})

        print("Scala Command window: "+str(self.window.id()))

        print("Scala output index: "+str(self.window.get_view_index(self.outputPanel)))


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

                #"existingOutput" : self.outputPanel.buffer_id()
                #Exec2Command.existingOutput =  self.outputPanel

                exec2_existing_output = self.outputPanel

                self.window.run_command('exec2',
                    {
                        "shell_cmd": "cd "+scalaFolder+" && mvn compile",
                        "encoding" : "UTF-8",
                        "file_regex": "^\[error\] (.+):([0-9]+): (.+)$"

                    })

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




