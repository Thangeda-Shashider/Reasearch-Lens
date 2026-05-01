import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchGraph } from '../api/client'
import * as d3 from 'd3'
import { SkeletonChart } from './LoadingSkeleton'

const TOPIC_COLORS = [
  '#6C63FF','#10B981','#F59E0B','#EF4444','#3B82F6',
  '#EC4899','#8B5CF6','#14B8A6','#F97316','#06B6D4',
]

export default function CitationGraph() {
  const svgRef = useRef(null)
  const { data, isLoading, error } = useQuery({
    queryKey: ['graph'],
    queryFn: fetchGraph,
  })

  useEffect(() => {
    if (!data?.nodes?.length || !svgRef.current) return

    const { nodes, links } = data
    const width = svgRef.current.parentElement.clientWidth || 700
    const height = 480

    d3.select(svgRef.current).selectAll('*').remove()

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)

    const defs = svg.append('defs')
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#4A5568')

    const topicIds = [...new Set(nodes.map(n => n.topic_id))]
    const colorMap = {}
    topicIds.forEach((tid, i) => {
      colorMap[tid] = tid == null ? '#4A5568' : TOPIC_COLORS[i % TOPIC_COLORS.length]
    })

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => Math.max(8, d.in_degree * 2) + 5))

    const link = svg.append('g').selectAll('line')
      .data(links).join('line')
      .attr('stroke', '#2A2F45')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)')

    const node = svg.append('g').selectAll('circle')
      .data(nodes).join('circle')
      .attr('r', d => Math.max(6, Math.min(20, 6 + d.in_degree * 2.5)))
      .attr('fill', d => colorMap[d.topic_id])
      .attr('fill-opacity', d => d.in_degree === 0 ? 0.5 : 0.9)
      .attr('stroke', d => d.in_degree === 0 ? '#EF4444' : 'transparent')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
      )

    // Tooltip
    const tooltip = d3.select(svgRef.current.parentElement)
      .append('div')
      .style('position', 'absolute')
      .style('pointer-events', 'none')
      .style('opacity', 0)
      .style('background', '#1E2130')
      .style('border', '1px solid #2A2F45')
      .style('border-radius', '10px')
      .style('padding', '8px 12px')
      .style('font-size', '12px')
      .style('color', '#E2E8F0')
      .style('max-width', '200px')

    node.on('mouseover', (event, d) => {
      tooltip.transition().duration(100).style('opacity', 1)
      tooltip.html(`<strong>${d.title || `Paper ${d.id}`}</strong><br>In-degree: ${d.in_degree}<br>${d.topic_label || ''}`)
        .style('left', (event.offsetX + 12) + 'px')
        .style('top', (event.offsetY - 10) + 'px')
    }).on('mouseout', () => {
      tooltip.transition().duration(100).style('opacity', 0)
    })

    sim.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      node.attr('cx', d => d.x).attr('cy', d => d.y)
    })

    return () => { tooltip.remove(); sim.stop() }
  }, [data])

  if (isLoading) return <SkeletonChart />
  if (error || !data?.nodes?.length) return (
    <div className="card p-8 text-center text-text-muted">
      <p>Run analysis to generate the citation graph.</p>
    </div>
  )

  return (
    <div className="card p-6">
      <h2 className="text-base font-semibold text-text-primary mb-1">Citation Network</h2>
      <p className="text-xs text-text-muted mb-4">
        Node size = citation count · <span className="text-danger">Red ring</span> = low-degree (potential gap) · Drag to explore
      </p>
      <div className="relative overflow-hidden rounded-xl bg-bg">
        <svg ref={svgRef} width="100%" height={480} />
      </div>
    </div>
  )
}
