#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.widgets import myPaginateDataGrid
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *
from beaker.server.recipetasks import RecipeTasks
#from turbogears.scheduler import add_interval_task
from beaker.server.scheduler import add_onetime_task
from socket import gethostname
import exceptions
import time

import cherrypy

from model import *
import string

import logging
log = logging.getLogger(__name__)

class Recipes(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    tasks = RecipeTasks()

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def upload_console(self, recipe_id, data):
        """
        upload the console log in pieces 
        """
        raise NotImplementedError

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Abort(self, recipe_id, msg):
        """
        Set recipe status to Aborted
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        return recipe.Abort(msg)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def Cancel(self, recipe_id):
        """
        Set recipe status to Cancelled
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipe ID: %s' % recipe_id))
        return recipe.Cancel(msg)

    @cherrypy.expose
    def to_xml(self, id):
        recipexml = Recipe.by_id(id).to_xml().toprettyxml()
        return dict(xml=recipexml)

    @expose(template='beaker.server.templates.grid')
    @paginate('list',default_order='-id')
    def index(self, *args, **kw):
        recipes = session.query(MachineRecipe)
        recipes_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='id', getter=lambda x:x.id, title='ID', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='whiteboard', getter=lambda x:x.whiteboard, title='Whiteboard', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='arch', getter=lambda x:x.arch, title='Arch', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='system', getter=lambda x: make_system_link(x.system), title='System', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='distro', getter=lambda x: make_distro_link(x.distro), title='Distro', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='progress', getter=lambda x: make_progress_bar(x), title='Progress', options=dict(sortable=False)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
                    ])
        return dict(title="Recipes", grid=recipes_grid, list=recipes, search_bar=None)

def new_recipes(*args):
    while True:
        recipes = Recipe.query().filter(
                Recipe.status==TaskStatus.by_name(u'New'))
        if recipes.count():
            log.debug("Entering new_recipes routine")
        for recipe in recipes:
            if recipe.distro:
                systems = recipe.distro.systems_filter(
                                            recipe.recipeset.job.owner,
                                            recipe.host_requires
                                                      )
                recipe.systems = []
                for system in systems:
                    # Add matched systems to recipe.
                    recipe.systems.append(system)
                if recipe.systems:
                    recipe.Process()
                    log.info("recipe ID %s moved from New to Processed" % recipe.id)
                else:
                    log.info("recipe ID %s moved from New to Aborted" % recipe.id)
                    recipe.recipeset.Abort('Recipe ID %s does not match any systems' % recipe.id)
            else:
                recipe.recipeset.Abort('Recipe ID %s does not have a distro' % recipe.id)
        session.flush()
        if recipes.count():
            log.debug("Exiting new_recipes routine")
        else:
            time.sleep(20)

def processed_recipesets(*args):
    while True:
        recipesets = RecipeSet.query()\
                           .join(['recipes','status'])\
                           .filter(Recipe.status==TaskStatus.by_name(u'Processed'))
        if recipesets.count():
            log.debug("Entering processed_recipes routine")
        for recipeset in recipesets:
            bad_l_controllers = set()
            # We only need to do this processing on multi-host recipes
            if len(recipeset.recipes) == 1:
                log.info("recipe ID %s moved from Processed to Queued" % recipeset.recipes[0].id)
                recipeset.recipes[0].Queue()
                continue
    
            # Find all the lab controllers that this recipeset may run.
            rsl_controllers = set(LabController.query()\
                                          .join(['systems',
                                                 'queued_recipes',
                                                 'recipeset'])\
                                          .filter(RecipeSet.id==recipeset.id).all())
    
            # Any lab controllers that are not associated to all recipes in the
            # recipe set must have those systems on that lab controller removed
            # from any recipes.  For multi-host all recipes must be schedulable
            # on one lab controller
            for recipe in recipeset.recipes:
                rl_controllers = set(LabController.query()\
                                           .join(['systems',
                                                  'queued_recipes'])\
                                           .filter(Recipe.id==recipe.id).all())
                bad_l_controllers = bad_l_controllers.union(rl_controllers.difference(rsl_controllers))
    
            for l_controller in rsl_controllers:
                enough_systems = False
                for recipe in recipeset.recipes:
                    systems = recipe.dyn_systems.filter(
                                              System.lab_controller==l_controller
                                                       ).all()
                    if len(systems) < len(recipeset.recipes):
                        break
                else:
                    # There are enough choices We don't need to worry about dead
                    # locks
                    enough_systems = True
                if not enough_systems:
                    # Eliminate bad choices.
                    for recipe in recipeset.recipes_orderby(l_controller)[:]:
                        for tmprecipe in recipeset.recipes:
                            systemsa = set(recipe.dyn_systems.filter(
                                              System.lab_controller==l_controller
                                                                    ).all())
                            systemsb = set(tmprecipe.dyn_systems.filter(
                                              System.lab_controller==l_controller
                                                                       ).all())
    
                            if systemsa.difference(systemsb):
                                for rem_system in systemsa.intersection(systemsb):
                                    log.debug("Removing %s from recipe id %s" % (rem_system, recipe.id))
                                    recipe.systems.remove(rem_system)
                    for recipe in recipeset.recipes:
                        count = 0
                        systems = recipe.dyn_systems.filter(
                                          System.lab_controller==l_controller
                                                           ).all()
                        for tmprecipe in recipeset.recipes:
                            tmpsystems = tmprecipe.dyn_systems.filter(
                                              System.lab_controller==l_controller
                                                                     ).all()
                            if recipe != tmprecipe and \
                               systems == tmpsystems:
                                count += 1
                        if len(systems) <= count:
                            # Remove all systems from this lc on this rs.
                            bad_l_controllers = bad_l_controllers.union([l_controller])
    
            # Remove systems that are on bad lab controllers
            # This means one of the recipes can be fullfilled on a lab controller
            # but not the rest of the recipes in the recipeSet.
            # This could very well remove ALL systems from all recipes in this
            # recipeSet.  If that happens then the recipeSet cannot be scheduled
            # and will be aborted by the abort process.
            for recipe in recipeset.recipes:
                for l_controller in bad_l_controllers:
                    systems = (recipe.dyn_systems.filter(
                                              System.lab_controller==l_controller
                                                    ).all()
                                  )
                    log.debug("Removing lab %s from recipe id %s" % (l_controller, recipe.id))
                    for system in systems:
                        log.debug("Removing %s from recipe id %s" % (system, recipe.id))
                        recipe.systems.remove(system)
                if recipe.systems:
                    # Set status to Queued 
                    log.info("recipe ID %s moved from Processed to Queued" % recipe.id)
                    recipe.Queue()
                else:
                    # Set status to Aborted 
                    log.info("recipe ID %s moved from Processed to Aborted" % recipe.id)
                    recipe.recipeset.Abort('Recipe ID %s does not match any systems' % recipe.id)
                        
        session.flush()
        if recipesets.count():
            log.debug("Exiting processed_recipes routine")
        else:
            time.sleep(20)

def queued_recipes(*args):
    while True:
        recipes = Recipe.query()\
                        .join('status')\
                        .join('systems')\
                        .join('recipeset')\
                        .filter(
                             or_(
                             and_(Recipe.status==TaskStatus.by_name(u'Queued'),
                                  System.user==None,
                                  RecipeSet.lab_controller==None
                                 ),
                             and_(Recipe.status==TaskStatus.by_name(u'Queued'),
                                  System.user==None,
                                  RecipeSet.lab_controller_id==System.lab_controller_id
                                 )
                                )
                               )
        count = recipes.count()
        if count:
            log.debug("Entering queued_recipes routine")
        for recipe in recipes:
            system = recipe.dyn_systems.filter(System.user==None)
            if recipe.recipeset.lab_controller:
                # First recipe of a recipeSet determines the lab_controller
                system = system.filter(
                             System.lab_controller==recipe.recipeset.lab_controller
                                      )
            system = system.first()
            if system:
                log.debug("System : %s is available for Recipe %s" % (system, recipe.id))
                # Atomic operation to put recipe in Scheduled state
                if session.connection(Recipe).execute(recipe_table.update(
                     and_(recipe_table.c.id==recipe.id,
                       recipe_table.c.status_id==TaskStatus.by_name(u'Queued').id)),
                       status_id=TaskStatus.by_name(u'Scheduled').id).rowcount == 1:
                    # Even though the above put the recipe in the "Scheduled" state
                    # it did not execute the update_status method.
                    recipe.Schedule()
                    # Atomic operation to reserve the system
                    if session.connection(System).execute(system_table.update(
                         and_(system_table.c.id==system.id,
                          system_table.c.user_id==None)),
                          user_id=recipe.recipeset.job.owner.user_id).rowcount == 1:
                        recipe.system = system
                        recipe.recipeset.lab_controller = system.lab_controller
                        recipe.systems = []
                        # Create the watchdog without an Expire time.
                        log.debug("Created watchdog for recipe id: %s and system: %s" % (recipe.id, system))
                        recipe.watchdog = Watchdog(system=recipe.system)
                        activity = SystemActivity(recipe.recipeset.job.owner, "Scheduler", "Reserved", "User", "", "%s" % recipe.recipeset.job.owner )
                        system.activity.append(activity)
                        log.info("recipe ID %s moved from Queued to Scheduled" % recipe.id)
                    else:
                        # The system was taken from underneath us.  Put recipe
                        # back into queued state and try again.
                        recipe.Queue()
                else:
                    #Some other thread beat us. Skip this recipe now.
                    # Depending on scheduler load it should be safe to run multiple
                    # Queued processes..  Also, systems that we don't directly
                    # control, for example, systems at a remote location that can
                    # pull jobs but not have any pushed onto them.  These systems
                    # could take a recipe and put it in running state. Not sure how
                    # to deal with multi-host jobs at remote locations.  May need to
                    # enforce single recipes for remote execution.
                    pass
        session.flush()
        if count:
            log.debug("Exiting queued_recipes routine")
        else:
            time.sleep(20)

def scheduled_recipes(*args):
    """
    if All recipes in a recipeSet are in Scheduled state then move them to
     Running.
    """
    while True:
        recipesets = RecipeSet.query().from_statement(
                            select([recipe_set_table.c.id, 
                                    func.min(recipe_table.c.status_id)],
                                   from_obj=[recipe_set_table.join(recipe_table)])\
                                   .group_by(RecipeSet.id)\
                                   .having(func.min(recipe_table.c.status_id) == TaskStatus.by_name(u'Scheduled').id)).all()
    
        if recipesets:
            log.debug("Entering scheduled_recipes routine")
        for recipeset in recipesets:
            # Go through each recipe in the recipeSet
            for recipe in recipeset.recipes:
                # If one of the recipes gets aborted then don't try and run
                if recipe.status != TaskStatus.by_name(u'Scheduled'):
                    continue
                recipe.Waiting()
                # Go Through each task and find out the roles of everyone else
                for i, task in enumerate(recipe.tasks):
                    for peer in recipe.recipeset.recipes:
                        # Roles are only shared amongst like recipe types
                        if type(recipe) == type(peer):
                            key = peer.tasks[i].role
                            task.roles[key].append(peer.system)
    
                # Start the first task in the recipe
                try:
                    recipe.tasks[0].Start()
                except exceptions.Exception, e:
                    log.error("Failed to Start recipe %s, due to %s" % (recipe.id,e))
                    recipe.recipeset.Abort(u"Failed to provision recipeid %s, %s" % 
                                                                             (
                                                                         recipe.id,
                                                                            e))
                # FIXME add customrepos if present
                ks_meta = "beaker=%s recipeid=%s packages=%s" % (
                                                          gethostname(),
                                                          recipe.id,
                                                          recipe.packages,
                                                                 )
                try:
                    recipe.system.action_auto_provision(recipe.distro,
                                                     ks_meta,
                                                     recipe.kernel_options,
                                                     recipe.kernel_options_post,
                                                     recipe.kickstart)
                    recipe.system.activity.append(
                         SystemActivity(recipe.recipeset.job.owner, 
                                        'Scheduler', 
                                        'Provision', 
                                        'Distro',
                                        '',
                                        '%s' % recipe.distro))
                except exceptions.Exception, e:
                    log.error(u"Failed to provision recipeid %s, %s" % (
                                                                         recipe.id,
                                                                            e))
                    recipe.recipeset.Abort(u"Failed to provision recipeid %s, %s" % 
                                                                             (
                                                                         recipe.id,
                                                                            e))
       
        session.flush()
        if recipesets:
            log.debug("Exiting scheduled_recipes routine")
        else:
            time.sleep(20)

def schedule():
    add_onetime_task(action=new_recipes,
                      args=[lambda:datetime.now()])
    add_onetime_task(action=processed_recipesets,
                      args=[lambda:datetime.now()],
                      initialdelay=5)
    add_onetime_task(action=queued_recipes,
                      args=[lambda:datetime.now()],
                      initialdelay=10)
    add_onetime_task(action=scheduled_recipes,
                      args=[lambda:datetime.now()],
                      initialdelay=15)
