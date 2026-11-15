// load the recommendations dataset into TinkerGraph every time the server starts
def globals = [:]
globals << [hook : [
  onStartUp: { ctx ->
    graph.io(IoCore.graphml()).readGraph('data/recommendations.graphml')
    ctx.logger.info("Loaded vertices: " + graph.traversal().V().count().next() + ", edges: " + graph.traversal().E().count().next())
  }
] as LifeCycleHook]
globals << [g : graph.traversal()]
