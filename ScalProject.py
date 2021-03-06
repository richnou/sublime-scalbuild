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

import threading

import ScalBuild


'''
This Class Describes a project, with informations about it, and dependencies etc...
'''
class ScalBuildProject(ScalBuild.Exec2.ProcessStatusListener):

    ## Build is required is some sources of the project changed
    buildRequired = True

    ## On Build Command finish, do stuff depending on return code for example
    def on_finished(self,proc):

        ## If Exit code is not 0 -> build was not successful
        if proc.exit_code() != 0 and proc.exit_code() != None:
            self.buildRequired = True
        else:
            self.buildRequired = False

        ## Release finished semaphore
        self.finishedSemaphore.release()

    def wait_finished(self):
        self.finishedSemaphore.acquire()

    def printlnToOutput(self,string):
        if self.dataListener:
            self.dataListener.println(string)
        else:
            print(string)

    def __init__(self, projectPath=None):

        ## Executor Sync
        ###################
        self.finishedSemaphore = threading.Semaphore()


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

            ## Try to Update local infos from parent if necessary
            if hasattr(self,'parent'):
                if self.groupId == None:
                    self.groupId = self.parent['groupId']
                if self.version == None:
                    self.version = self.parent['version']


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
    def build(self,buildTarget="install",rebuild=False):

        ## Rebuild ?
        if rebuild == True:
            self.printlnToOutput("["+self.artifactId+"] Forcing re-Building")
            self.buildRequired = True

        ## Remove possibly not acquired finished grant
        #############
        self.finishedSemaphore.acquire(False)

        self.printlnToOutput("["+self.artifactId+"] Building")

        if self.buildSystem == "sbt":

            self.printlnToOutput("["+artifactId+"] Building Using sbt")

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

            self.printlnToOutput("["+self.artifactId+"] Building Using maven and goal "+buildTarget)

            ## Check if we need to build dependencies
            ########################
            for dependency in self.dependencies:

                ## Is dependency also a project?
                dependencyProject = ScalBuild.ScalBuild.scalBuildGetProject(dependency["groupId"],dependency["artifactId"],dependency["version"])
                if dependencyProject!=None:
                    self.printlnToOutput("["+self.artifactId+"] -> Dependency "+str(dependency)+" is a ScalBuild Project")
                    if dependencyProject.buildRequired == True:
                        self.buildRequired = True
                        self.printlnToOutput("["+dependency["artifactId"]+"]   -> Build Required")
                        dependencyProject.build()
                        dependencyProject.wait_finished()
                    else:
                        self.printlnToOutput("["+dependency["artifactId"]+"]   -> Build Not Required")

            ## Change output parameters
            ###############################
            self.dataListener.setOutputSetting("result_base_dir", self.projectPath)
            self.dataListener.setOutputSetting("result_file_regex", "^\[(?:(?i)ERROR|WARNING)\] (.+):([0-9]+): (.+)$")

            ## Create Executor
            ############################
            executor = ScalBuild.Exec2.CommandExecutor(self.dataListener,self)

            ## Build
            ################
            if self.buildRequired == False:
                self.printlnToOutput("["+self.artifactId+"]  Build Not Required (unchanged sources and dependencies)")
            else:

                ## If Build successful -> Build not required anymore
                ## Build required is updated in on_finished method as ProcessStatusListener
                executor.run( shell_cmd = "cd "+self.projectPath+" && mvn "+buildTarget, encoding =  "UTF-8" )

        else:
            self.printlnToOutput("["+self.artifactId+"] Unsupported buildSystem")


    ## Returns String id (groupId:artifactId:version)
    def strId(self):
        return self.groupId+":"+self.artifactId+":"+self.version

