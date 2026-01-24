import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  Box,
  Container,
  VStack,
  HStack,
  Heading,
  Text,
  Input,
  Select,
  Button,
  Badge,
  Progress,
  Grid,
  GridItem,
  IconButton,
  Checkbox,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  Card,
  CardBody,
  Image,
  Flex,
  Spacer,
  Spinner,
  Alert,
  AlertIcon,
  Code,
  Collapse,
  AspectRatio,
  Tooltip,
} from '@chakra-ui/react'

const API_BASE = '/api'

function App() {
  const [url, setUrl] = useState('')
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedJob, setExpandedJob] = useState(null)
  const [logs, setLogs] = useState([])
  const [captionStyles, setCaptionStyles] = useState([])
  const [selectedStyle, setSelectedStyle] = useState('default')
  const [aiAvailable, setAiAvailable] = useState(false)
  const [useAi, setUseAi] = useState(false)
  const [sortBy, setSortBy] = useState('recent')
  const [filterStatus, setFilterStatus] = useState('all')
  const [previewVideo, setPreviewVideo] = useState(null)
  const [previewJob, setPreviewJob] = useState(null)
  const [chapterSelectJob, setChapterSelectJob] = useState(null)
  const [chapters, setChapters] = useState([])
  const [selectedClips, setSelectedClips] = useState(new Set())

  const { isOpen: isPreviewOpen, onOpen: onPreviewOpen, onClose: onPreviewClose } = useDisclosure()
  const { isOpen: isChapterOpen, onOpen: onChapterOpen, onClose: onChapterClose } = useDisclosure()

  useEffect(() => {
    fetchJobs()
    fetchCaptionStyles()
    fetchDetectionModes()
    const interval = setInterval(fetchJobs, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!expandedJob) {
      setLogs([])
      return
    }
    fetchLogs(expandedJob)
    const interval = setInterval(() => fetchLogs(expandedJob), 2000)
    return () => clearInterval(interval)
  }, [expandedJob])

  const autoOpenedJobs = useRef(new Set())

  useEffect(() => {
    const readyJob = jobs.find(j => j.status === 'chapters_ready')
    if (readyJob && !autoOpenedJobs.current.has(readyJob.id) && readyJob.id !== chapterSelectJob?.id) {
      if (chapterSelectJob) return
      fetchChapters(readyJob.id)
      setChapterSelectJob(readyJob)
      autoOpenedJobs.current.add(readyJob.id)
      onChapterOpen()
    }
    if (chapterSelectJob) {
      const currentJobStatus = jobs.find(j => j.id === chapterSelectJob.id)?.status
      if (currentJobStatus && currentJobStatus !== 'chapters_ready') {
        setChapterSelectJob(null)
        setChapters([])
        onChapterClose()
      }
    }
  }, [jobs, chapterSelectJob])

  const fetchChapters = useCallback(async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/chapters`)
      if (res.ok) {
        const data = await res.json()
        setChapters(data.chapters || [])
      }
    } catch (err) {
      console.error('Failed to fetch chapters:', err)
    }
  }, [])

  const fetchCaptionStyles = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/caption-styles`)
      if (res.ok) {
        const data = await res.json()
        setCaptionStyles(data.styles || [])
      }
    } catch (err) {
      console.error('Failed to fetch caption styles:', err)
    }
  }, [])

  const fetchDetectionModes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/detection-modes`)
      if (res.ok) {
        const data = await res.json()
        setAiAvailable(data.ai_configured || false)
      }
    } catch (err) {
      console.error('Failed to fetch detection modes:', err)
    }
  }, [])

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs`)
      if (res.ok) {
        const data = await res.json()
        setJobs(data.reverse())
      }
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    }
  }, [])

  const fetchLogs = useCallback(async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/logs`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  }, [])

  const submitJob = useCallback(async (e) => {
    e.preventDefault()
    if (!url.trim() || loading) return

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          caption_style: selectedStyle,
          auto_detect: true,
          use_ai_detection: useAi
        })
      })
      if (res.ok) {
        setUrl('')
        fetchJobs()
      }
    } catch (err) {
      console.error('Failed to submit job:', err)
    }
    setLoading(false)
  }, [url, loading, selectedStyle, useAi, fetchJobs])

  const deleteJob = useCallback(async (jobId) => {
    try {
      await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' })
      if (expandedJob === jobId) setExpandedJob(null)
      fetchJobs()
    } catch (err) {
      console.error('Failed to delete job:', err)
    }
  }, [expandedJob, fetchJobs])

  const getStatusColor = (status) => {
    const colors = {
      pending: 'yellow',
      downloading: 'blue',
      transcribing: 'purple',
      analyzing: 'cyan',
      chapters_ready: 'orange',
      processing: 'blue',
      completed: 'green',
      failed: 'red'
    }
    return colors[status] || 'gray'
  }

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pending',
      downloading: 'Downloading',
      transcribing: 'Transcribing',
      analyzing: 'Analyzing',
      chapters_ready: 'Select Chapters',
      processing: 'Processing',
      completed: 'Completed',
      failed: 'Failed'
    }
    return labels[status] || status
  }

  const formatETA = useCallback((seconds) => {
    if (!seconds || seconds <= 0) return null
    if (seconds < 60) return `~${seconds}s remaining`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `~${mins}m ${secs}s remaining`
  }, [])

  const filteredAndSortedJobs = useMemo(() => {
    let filtered = jobs
    if (filterStatus !== 'all') {
      filtered = filtered.filter(job => job.status === filterStatus)
    }
    const sorted = [...filtered]
    switch (sortBy) {
      case 'oldest':
        sorted.reverse()
        break
      case 'completed':
        sorted.sort((a, b) => {
          if (a.status === 'completed' && b.status !== 'completed') return -1
          if (a.status !== 'completed' && b.status === 'completed') return 1
          return 0
        })
        break
      case 'score':
        sorted.sort((a, b) => {
          const aMaxScore = Math.max(...(a.clips || []).map(c => c.score || 0), 0)
          const bMaxScore = Math.max(...(b.clips || []).map(c => c.score || 0), 0)
          return bMaxScore - aMaxScore
        })
        break
      default:
        break
    }
    return sorted
  }, [jobs, filterStatus, sortBy])

  const handlePreview = (clip, jobId) => {
    setPreviewVideo(clip)
    setPreviewJob(jobId)
    onPreviewOpen()
  }

  const toggleClipSelection = useCallback((jobId, clip) => {
    setSelectedClips(prev => {
      const next = new Set(prev)
      const clipId = `${jobId}_${clip.filename}`
      const existing = Array.from(next).find(c => c.id === clipId)
      if (existing) {
        next.delete(existing)
      } else {
        next.add({
          id: clipId,
          jobId,
          filename: clip.filename,
          url: `${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`
        })
      }
      return next
    })
  }, [])

  const downloadSelected = useCallback(() => {
    selectedClips.forEach((clip, index) => {
      setTimeout(() => {
        window.open(clip.url, '_blank')
      }, index * 500)
    })
  }, [selectedClips])

  return (
    <Box minH="100vh" bg="dark.900" py={8}>
      <Container maxW="7xl">
        {/* Header */}
        <VStack spacing={2} mb={10}>
          <Heading
            as="h1"
            size="2xl"
            bgGradient="linear(to-r, brand.400, pink.400, orange.400)"
            bgClip="text"
            fontWeight="extrabold"
          >
            Auto Clipper
          </Heading>
          <Badge colorScheme="purple" variant="subtle" px={3} py={1} borderRadius="full">
            No recurring fees - Run locally
          </Badge>
        </VStack>

        {/* Submit Form */}
        <Card bg="dark.700" mb={8}>
          <CardBody>
            <form onSubmit={submitJob}>
              <VStack spacing={4}>
                <Flex gap={4} w="100%" direction={{ base: 'column', md: 'row' }}>
                  <Input
                    placeholder="Paste YouTube URL here..."
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={loading}
                    size="lg"
                    flex={1}
                  />
                  <Select
                    value={selectedStyle}
                    onChange={(e) => setSelectedStyle(e.target.value)}
                    disabled={loading}
                    size="lg"
                    w={{ base: '100%', md: '200px' }}
                  >
                    {captionStyles.map(style => (
                      <option key={style.id} value={style.id}>{style.name}</option>
                    ))}
                  </Select>
                  <Button
                    type="submit"
                    isLoading={loading}
                    loadingText="Submitting"
                    variant="primary"
                    size="lg"
                    px={8}
                    isDisabled={!url.trim()}
                  >
                    Create Clip
                  </Button>
                </Flex>

                <Checkbox
                  isChecked={useAi}
                  onChange={(e) => setUseAi(e.target.checked)}
                  isDisabled={!aiAvailable || loading}
                  colorScheme="purple"
                >
                  <HStack spacing={2}>
                    <Text>Use AI Detection</Text>
                    {!aiAvailable && (
                      <Text fontSize="xs" color="gray.500">(Add API key in .env)</Text>
                    )}
                  </HStack>
                </Checkbox>

                <Text fontSize="sm" color="gray.500">
                  {useAi && aiAvailable ? 'AI-powered detection (Gemini/OpenAI)' : 'Rule-based detection (free)'}
                  {' '} • Caption: {captionStyles.find(s => s.id === selectedStyle)?.name || 'Default'}
                </Text>
              </VStack>
            </form>
          </CardBody>
        </Card>

        {/* Batch Download Button */}
        {selectedClips.size > 0 && (
          <Box position="fixed" bottom={8} right={8} zIndex={40}>
            <Button
              onClick={downloadSelected}
              variant="primary"
              size="lg"
              leftIcon={<Text>⬇️</Text>}
              boxShadow="2xl"
            >
              Download ({selectedClips.size})
            </Button>
          </Box>
        )}

        {/* Jobs Section */}
        <Box>
          <Flex align="center" justify="space-between" mb={6} wrap="wrap" gap={4}>
            <Heading size="lg">Your Clips</Heading>
            {jobs.length > 0 && (
              <HStack spacing={3}>
                <Select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  size="sm"
                  w="140px"
                >
                  <option value="all">All Status</option>
                  <option value="completed">Completed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </Select>
                <Select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  size="sm"
                  w="140px"
                >
                  <option value="recent">Most Recent</option>
                  <option value="oldest">Oldest</option>
                  <option value="completed">Completed First</option>
                  <option value="score">Highest Score</option>
                </Select>
              </HStack>
            )}
          </Flex>

          {jobs.length === 0 ? (
            <Card bg="dark.700" p={12}>
              <Text textAlign="center" color="gray.500" fontSize="lg">
                No clips yet. Paste a YouTube URL above to get started!
              </Text>
            </Card>
          ) : (
            <VStack spacing={4} align="stretch">
              {filteredAndSortedJobs.map(job => (
                <Card key={job.id} bg="dark.700">
                  <CardBody>
                    <Flex gap={6} direction={{ base: 'column', lg: 'row' }}>
                      {/* Job Info */}
                      <VStack align="start" spacing={3} flex={1}>
                        <Text fontSize="sm" color="gray.500" isTruncated maxW="400px">
                          {job.url}
                        </Text>

                        <HStack spacing={3} wrap="wrap">
                          <Badge
                            colorScheme={getStatusColor(job.status)}
                            px={3}
                            py={1}
                            borderRadius="md"
                          >
                            <HStack spacing={1}>
                              {['downloading', 'transcribing', 'processing'].includes(job.status) && (
                                <Spinner size="xs" />
                              )}
                              <Text>{getStatusLabel(job.status)}</Text>
                            </HStack>
                          </Badge>
                          {job.eta_seconds && (
                            <Text fontSize="xs" color="gray.500">
                              {formatETA(job.eta_seconds)}
                            </Text>
                          )}
                        </HStack>

                        {job.status !== 'completed' && job.status !== 'failed' && (
                          <Progress
                            value={job.progress}
                            size="sm"
                            colorScheme="purple"
                            borderRadius="full"
                            w="100%"
                            hasStripe
                            isAnimated
                          />
                        )}

                        {job.status === 'chapters_ready' && (
                          <Button
                            variant="primary"
                            w="100%"
                            onClick={() => {
                              fetchChapters(job.id)
                              setChapterSelectJob(job)
                              onChapterOpen()
                            }}
                          >
                            Select Chapters to Continue
                          </Button>
                        )}

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                        >
                          {expandedJob === job.id ? '▼ Hide Logs' : '▶ Show Logs'}
                        </Button>

                        <Collapse in={expandedJob === job.id} animateOpacity>
                          <Box
                            bg="dark.900"
                            borderRadius="md"
                            p={3}
                            maxH="200px"
                            overflowY="auto"
                            w="100%"
                            fontSize="xs"
                            fontFamily="mono"
                          >
                            {logs.length === 0 ? (
                              <Text color="gray.500">Waiting for logs...</Text>
                            ) : (
                              logs.map((line, i) => (
                                <Text key={i} color="gray.400">{line}</Text>
                              ))
                            )}
                          </Box>
                        </Collapse>

                        {job.error && (
                          <Alert status="error" borderRadius="md" size="sm">
                            <AlertIcon />
                            <Text fontSize="sm">{job.error}</Text>
                          </Alert>
                        )}
                      </VStack>

                      {/* Clips Grid */}
                      <HStack spacing={4} align="start">
                        {job.status === 'completed' && job.clips && job.clips.length > 0 && (
                          <Grid
                            templateColumns={{ base: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' }}
                            gap={3}
                          >
                            {job.clips.map((clip, idx) => {
                              const clipId = `${job.id}_${clip.filename}`
                              const isSelected = Array.from(selectedClips).some(c => c.id === clipId)
                              return (
                                <ClipCard
                                  key={idx}
                                  clip={clip}
                                  jobId={job.id}
                                  isSelected={isSelected}
                                  onPreview={() => handlePreview(clip, job.id)}
                                  onToggleSelect={() => toggleClipSelection(job.id, clip)}
                                />
                              )
                            })}
                          </Grid>
                        )}

                        <Tooltip label="Delete job">
                          <IconButton
                            icon={<Text>🗑️</Text>}
                            variant="ghost"
                            colorScheme="red"
                            onClick={() => deleteJob(job.id)}
                          />
                        </Tooltip>
                      </HStack>
                    </Flex>
                  </CardBody>
                </Card>
              ))}
            </VStack>
          )}
        </Box>
      </Container>

      {/* Video Preview Modal */}
      <Modal isOpen={isPreviewOpen} onClose={onPreviewClose} size="xl" isCentered>
        <ModalOverlay />
        <ModalContent bg="dark.800" maxW="500px">
          <ModalCloseButton />
          <ModalBody p={4}>
            {previewVideo && (
              <VStack spacing={4}>
                <AspectRatio ratio={9/16} w="100%">
                  <video
                    src={`${API_BASE}/jobs/${previewJob}/download?filename=${previewVideo.filename}`}
                    controls
                    autoPlay
                    style={{ borderRadius: '12px' }}
                  />
                </AspectRatio>
                <HStack w="100%" justify="space-between">
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="bold">{previewVideo.title || 'Viral Clip'}</Text>
                    <Text fontSize="sm" color="gray.500">~{Math.round(previewVideo.duration || 30)}s</Text>
                  </VStack>
                  <Button
                    as="a"
                    href={`${API_BASE}/jobs/${previewJob}/download?filename=${previewVideo.filename}`}
                    download
                    variant="primary"
                  >
                    Download
                  </Button>
                </HStack>
              </VStack>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Chapter Selection Modal */}
      <Modal isOpen={isChapterOpen} onClose={onChapterClose} size="2xl" scrollBehavior="inside">
        <ModalOverlay />
        <ModalContent bg="dark.800">
          <ModalHeader>Select Chapters to Clip</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <ChapterSelector
              jobId={chapterSelectJob?.id}
              chapters={chapters}
              onSubmit={() => {
                onChapterClose()
                setChapterSelectJob(null)
                setChapters([])
                fetchJobs()
              }}
              onCancel={onChapterClose}
            />
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  )
}

// ClipCard Component
function ClipCard({ clip, jobId, isSelected, onPreview, onToggleSelect }) {
  const thumbnailUrl = clip.thumbnail
    ? `${API_BASE}/jobs/${jobId}/thumbnail/${clip.thumbnail}`
    : null

  return (
    <Card
      bg="dark.600"
      overflow="hidden"
      cursor="pointer"
      transition="all 0.2s"
      _hover={{ transform: 'translateY(-4px)', boxShadow: 'lg' }}
      borderWidth={isSelected ? '2px' : '1px'}
      borderColor={isSelected ? 'brand.500' : 'gray.700'}
      position="relative"
    >
      <Box position="absolute" top={2} left={2} zIndex={2}>
        <Checkbox
          isChecked={isSelected}
          onChange={onToggleSelect}
          colorScheme="purple"
          size="lg"
          onClick={(e) => e.stopPropagation()}
        />
      </Box>

      <AspectRatio ratio={9/16}>
        <Box bg="dark.500">
          {thumbnailUrl ? (
            <Image
              src={thumbnailUrl}
              alt={clip.title}
              objectFit="cover"
              w="100%"
              h="100%"
            />
          ) : (
            <Flex align="center" justify="center" h="100%">
              <Text fontSize="4xl">🎬</Text>
            </Flex>
          )}
        </Box>
      </AspectRatio>

      <CardBody p={3}>
        <VStack align="start" spacing={2}>
          <HStack justify="space-between" w="100%">
            <Badge colorScheme="green" fontSize="xs">
              👍 /{clip.score || 10}
            </Badge>
            <Text fontSize="xs" color="gray.500">
              ~{Math.round(clip.duration || 30)}s
            </Text>
          </HStack>
          <Text fontSize="sm" fontWeight="medium" noOfLines={1}>
            {clip.title || 'Viral Clip'}
          </Text>
          <HStack w="100%" spacing={2}>
            <Button size="xs" variant="ghost" flex={1} onClick={onPreview}>
              👁️ Preview
            </Button>
            <Button
              as="a"
              href={`${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`}
              download
              size="xs"
              variant="primary"
              flex={1}
            >
              ⬇️ Download
            </Button>
          </HStack>
        </VStack>
      </CardBody>
    </Card>
  )
}

// ChapterSelector Component
function ChapterSelector({ jobId, chapters, onSubmit, onCancel }) {
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const toggleChapter = (chapterId) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(chapterId)) {
        next.delete(chapterId)
      } else {
        next.add(chapterId)
      }
      return next
    })
  }

  const selectAll = () => setSelected(new Set(chapters.map(ch => ch.id)))
  const selectNone = () => setSelected(new Set())

  const handleSubmit = async () => {
    if (selected.size === 0) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/select-chapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chapter_ids: Array.from(selected) })
      })
      if (res.ok) {
        onSubmit()
      } else {
        const data = await res.json()
        setError(data.detail || 'Failed to submit chapters')
      }
    } catch (err) {
      setError('Network error. Please try again.')
    }
    setLoading(false)
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    if (mins > 0) return `${mins}m ${secs}s`
    return `${secs}s`
  }

  const totalDuration = chapters
    .filter(ch => selected.has(ch.id))
    .reduce((sum, ch) => sum + ch.duration, 0)

  return (
    <VStack spacing={4} align="stretch">
      <HStack justify="space-between">
        <Text color="gray.400" fontSize="sm">
          Choose which chapters to convert into video clips
        </Text>
        <HStack>
          <Button size="sm" variant="ghost" onClick={selectAll}>Select All</Button>
          <Button size="sm" variant="ghost" onClick={selectNone}>Clear</Button>
        </HStack>
      </HStack>

      {selected.size > 0 && (
        <Alert status="info" borderRadius="md" bg="brand.900" border="1px" borderColor="brand.700">
          <HStack justify="space-between" w="100%">
            <Text color="brand.300">
              {selected.size} chapter{selected.size !== 1 ? 's' : ''} selected
            </Text>
            <Text color="gray.400" fontSize="sm">
              Total duration: {formatDuration(totalDuration)}
            </Text>
          </HStack>
        </Alert>
      )}

      {error && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}

      <VStack spacing={2} align="stretch" maxH="400px" overflowY="auto">
        {chapters.map((chapter, index) => (
          <Card
            key={chapter.id}
            bg={selected.has(chapter.id) ? 'brand.900' : 'dark.600'}
            borderWidth="2px"
            borderColor={selected.has(chapter.id) ? 'brand.500' : 'transparent'}
            cursor="pointer"
            onClick={() => toggleChapter(chapter.id)}
            transition="all 0.2s"
            _hover={{ borderColor: 'brand.400' }}
          >
            <CardBody py={3} px={4}>
              <HStack spacing={4}>
                <Checkbox
                  isChecked={selected.has(chapter.id)}
                  onChange={() => toggleChapter(chapter.id)}
                  colorScheme="purple"
                  onClick={(e) => e.stopPropagation()}
                />
                <VStack align="start" spacing={1} flex={1}>
                  <HStack>
                    <Badge size="sm" colorScheme="gray">#{index + 1}</Badge>
                    <Text fontWeight="semibold" noOfLines={1}>{chapter.title}</Text>
                  </HStack>
                  <HStack fontSize="sm" color="gray.400">
                    <Text>{formatTime(chapter.start)} - {formatTime(chapter.end)}</Text>
                    <Text color="brand.400">{formatDuration(chapter.duration)}</Text>
                  </HStack>
                  {chapter.summary && (
                    <Text fontSize="sm" color="gray.500" noOfLines={2}>{chapter.summary}</Text>
                  )}
                </VStack>
                {chapter.confidence && (
                  <Badge
                    colorScheme={chapter.confidence >= 0.8 ? 'green' : chapter.confidence >= 0.5 ? 'yellow' : 'gray'}
                  >
                    {Math.round(chapter.confidence * 100)}%
                  </Badge>
                )}
              </HStack>
            </CardBody>
          </Card>
        ))}
      </VStack>

      <HStack spacing={4} pt={2}>
        <Button flex={1} variant="ghost" onClick={onCancel} isDisabled={loading}>
          Cancel
        </Button>
        <Button
          flex={1}
          variant="primary"
          onClick={handleSubmit}
          isDisabled={selected.size === 0}
          isLoading={loading}
          loadingText="Processing..."
        >
          Create {selected.size} Clip{selected.size !== 1 ? 's' : ''}
        </Button>
      </HStack>
    </VStack>
  )
}

export default App
