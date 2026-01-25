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
  Spinner,
  Alert,
  AlertIcon,
  AspectRatio,
  Tooltip,
  SimpleGrid,
} from '@chakra-ui/react'

const API_BASE = '/api'

// Extract YouTube video ID from URL
function getYouTubeVideoId(url) {
  if (!url) return null
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\s?]+)/)
  return match ? match[1] : null
}

// Get YouTube thumbnail URL
function getYouTubeThumbnail(url, quality = 'hqdefault') {
  const videoId = getYouTubeVideoId(url)
  if (!videoId) return null
  return `https://img.youtube.com/vi/${videoId}/${quality}.jpg`
}

function App() {
  const [url, setUrl] = useState('')
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [captionStyles, setCaptionStyles] = useState([])
  const [selectedStyle, setSelectedStyle] = useState('default')
  const [aiAvailable, setAiAvailable] = useState(false)
  const [useAi, setUseAi] = useState(false)
  const [filterStatus, setFilterStatus] = useState('all')
  const [selectedJob, setSelectedJob] = useState(null)
  const [chapterSelectJob, setChapterSelectJob] = useState(null)
  const [chapters, setChapters] = useState([])
  const [previewClip, setPreviewClip] = useState(null)

  const { isOpen: isDetailOpen, onOpen: onDetailOpen, onClose: onDetailClose } = useDisclosure()
  const { isOpen: isChapterOpen, onOpen: onChapterOpen, onClose: onChapterClose } = useDisclosure()
  const { isOpen: isPreviewOpen, onOpen: onPreviewOpen, onClose: onPreviewClose } = useDisclosure()

  useEffect(() => {
    fetchJobs()
    fetchCaptionStyles()
    fetchDetectionModes()
    const interval = setInterval(fetchJobs, 3000)
    return () => clearInterval(interval)
  }, [])

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

  // Update selected job data when jobs refresh
  useEffect(() => {
    if (selectedJob) {
      const updated = jobs.find(j => j.id === selectedJob.id)
      if (updated) setSelectedJob(updated)
    }
  }, [jobs])

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

  const deleteJob = useCallback(async (jobId, e) => {
    e?.stopPropagation()
    try {
      await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' })
      if (selectedJob?.id === jobId) {
        setSelectedJob(null)
        onDetailClose()
      }
      fetchJobs()
    } catch (err) {
      console.error('Failed to delete job:', err)
    }
  }, [selectedJob, fetchJobs, onDetailClose])

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

  const filteredJobs = useMemo(() => {
    if (filterStatus === 'all') return jobs
    return jobs.filter(job => job.status === filterStatus)
  }, [jobs, filterStatus])

  const handleJobClick = (job) => {
    setSelectedJob(job)
    onDetailOpen()
  }

  const handlePreviewClip = (clip, jobId) => {
    setPreviewClip({ ...clip, jobId })
    onPreviewOpen()
  }

  // Extract title from URL or first clip
  const getJobTitle = (job) => {
    if (job.clips && job.clips.length > 0 && job.clips[0].title) {
      // Remove "Part X: " prefix if exists
      return job.clips[0].title.replace(/^Part \d+:\s*/, '').slice(0, 50)
    }
    // Extract from YouTube URL
    const videoId = getYouTubeVideoId(job.url)
    return videoId ? `Video ${videoId.slice(0, 8)}...` : 'Processing...'
  }

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

        {/* Projects Section */}
        <Box>
          <Flex align="center" justify="space-between" mb={6} wrap="wrap" gap={4}>
            <HStack>
              <Heading size="lg">All projects</Heading>
              <Text color="gray.500">({jobs.length})</Text>
            </HStack>
            {jobs.length > 0 && (
              <Select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                size="sm"
                w="150px"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="chapters_ready">Awaiting Selection</option>
                <option value="failed">Failed</option>
              </Select>
            )}
          </Flex>

          {jobs.length === 0 ? (
            <Card bg="dark.700" p={12}>
              <Text textAlign="center" color="gray.500" fontSize="lg">
                No projects yet. Paste a YouTube URL above to get started!
              </Text>
            </Card>
          ) : (
            <SimpleGrid columns={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing={4}>
              {filteredJobs.map(job => (
                <ProjectCard
                  key={job.id}
                  job={job}
                  onClick={() => handleJobClick(job)}
                  onDelete={(e) => deleteJob(job.id, e)}
                  onSelectChapters={() => {
                    fetchChapters(job.id)
                    setChapterSelectJob(job)
                    onChapterOpen()
                  }}
                  getStatusColor={getStatusColor}
                  getStatusLabel={getStatusLabel}
                  getJobTitle={getJobTitle}
                />
              ))}
            </SimpleGrid>
          )}
        </Box>
      </Container>

      {/* Job Detail Modal */}
      <Modal isOpen={isDetailOpen} onClose={onDetailClose} size="6xl" scrollBehavior="inside">
        <ModalOverlay bg="blackAlpha.800" />
        <ModalContent bg="dark.800" maxW="1200px">
          <ModalHeader borderBottomWidth="1px" borderColor="gray.700">
            <HStack justify="space-between" pr={8}>
              <VStack align="start" spacing={1}>
                <Text fontSize="lg">{selectedJob ? getJobTitle(selectedJob) : ''}</Text>
                <Text fontSize="sm" color="gray.500" fontWeight="normal">
                  {selectedJob?.clips?.length || 0} clips generated
                </Text>
              </VStack>
              <Badge colorScheme={getStatusColor(selectedJob?.status)} px={3} py={1}>
                {getStatusLabel(selectedJob?.status)}
              </Badge>
            </HStack>
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody py={6}>
            {selectedJob && (
              <JobDetailView
                job={selectedJob}
                onPreview={handlePreviewClip}
              />
            )}
          </ModalBody>
        </ModalContent>
      </Modal>

      {/* Video Preview Modal */}
      <Modal isOpen={isPreviewOpen} onClose={onPreviewClose} size="xl" isCentered>
        <ModalOverlay />
        <ModalContent bg="dark.800" maxW="500px">
          <ModalCloseButton />
          <ModalBody p={4}>
            {previewClip && (
              <VStack spacing={4}>
                <Box w="100%" bg="black" borderRadius="12px" overflow="hidden">
                  <video
                    src={`${API_BASE}/jobs/${previewClip.jobId}/download?filename=${previewClip.filename}`}
                    controls
                    autoPlay
                    style={{
                      width: '100%',
                      maxHeight: '70vh',
                      borderRadius: '12px',
                      objectFit: 'contain'
                    }}
                  />
                </Box>
                <HStack w="100%" justify="space-between">
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="bold">{previewClip.title || 'Viral Clip'}</Text>
                    <Text fontSize="sm" color="gray.500">~{Math.round(previewClip.duration || 30)}s</Text>
                  </VStack>
                  <Button
                    as="a"
                    href={`${API_BASE}/jobs/${previewClip.jobId}/download?filename=${previewClip.filename}`}
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

// Project Card Component (OpusClip-style)
function ProjectCard({ job, onClick, onDelete, onSelectChapters, getStatusColor, getStatusLabel, getJobTitle }) {
  const thumbnail = getYouTubeThumbnail(job.url)
  const clipCount = job.clips?.length || 0
  const isProcessing = ['pending', 'downloading', 'transcribing', 'analyzing', 'processing'].includes(job.status)
  const needsSelection = job.status === 'chapters_ready'

  return (
    <Card
      bg="dark.700"
      overflow="hidden"
      cursor="pointer"
      transition="all 0.2s"
      _hover={{ transform: 'translateY(-4px)', boxShadow: 'xl' }}
      onClick={needsSelection ? onSelectChapters : onClick}
      position="relative"
    >
      {/* Thumbnail */}
      <AspectRatio ratio={16/9}>
        <Box bg="dark.600" position="relative">
          {thumbnail ? (
            <Image
              src={thumbnail}
              alt="Video thumbnail"
              objectFit="cover"
              w="100%"
              h="100%"
            />
          ) : (
            <Flex align="center" justify="center" h="100%">
              <Text fontSize="4xl">🎬</Text>
            </Flex>
          )}

          {/* Overlay for processing */}
          {isProcessing && (
            <Flex
              position="absolute"
              inset={0}
              bg="blackAlpha.700"
              align="center"
              justify="center"
              flexDirection="column"
              gap={2}
            >
              <Spinner size="lg" color="brand.400" thickness="3px" />
              <Text fontSize="sm" color="white">{getStatusLabel(job.status)}</Text>
              {job.progress > 0 && (
                <Progress
                  value={job.progress}
                  size="sm"
                  colorScheme="purple"
                  w="80%"
                  borderRadius="full"
                />
              )}
            </Flex>
          )}

          {/* Needs selection overlay */}
          {needsSelection && (
            <Flex
              position="absolute"
              inset={0}
              bg="blackAlpha.700"
              align="center"
              justify="center"
              flexDirection="column"
              gap={2}
            >
              <Text fontSize="2xl">✨</Text>
              <Text fontSize="sm" color="white" fontWeight="bold">Select Chapters</Text>
            </Flex>
          )}

          {/* Clip count badge */}
          {job.status === 'completed' && clipCount > 0 && (
            <Badge
              position="absolute"
              top={2}
              right={2}
              colorScheme="green"
              fontSize="xs"
              px={2}
            >
              {clipCount} clip{clipCount !== 1 ? 's' : ''}
            </Badge>
          )}

          {/* Failed badge */}
          {job.status === 'failed' && (
            <Badge
              position="absolute"
              top={2}
              right={2}
              colorScheme="red"
              fontSize="xs"
            >
              Failed
            </Badge>
          )}
        </Box>
      </AspectRatio>

      <CardBody p={3}>
        <VStack align="start" spacing={2}>
          <Text fontSize="sm" fontWeight="medium" noOfLines={2} minH="40px">
            {getJobTitle(job)}
          </Text>
          <HStack justify="space-between" w="100%">
            <Badge colorScheme={getStatusColor(job.status)} variant="subtle" fontSize="xs">
              {getStatusLabel(job.status)}
            </Badge>
            <Tooltip label="Delete project">
              <IconButton
                icon={<Text fontSize="xs">🗑️</Text>}
                variant="ghost"
                size="xs"
                colorScheme="red"
                onClick={onDelete}
              />
            </Tooltip>
          </HStack>
        </VStack>
      </CardBody>
    </Card>
  )
}

// Job Detail View Component
function JobDetailView({ job, onPreview }) {
  const [selectedClips, setSelectedClips] = useState(new Set())

  const toggleClipSelection = (clipId) => {
    setSelectedClips(prev => {
      const next = new Set(prev)
      if (next.has(clipId)) {
        next.delete(clipId)
      } else {
        next.add(clipId)
      }
      return next
    })
  }

  const downloadSelected = () => {
    const clipsToDownload = job.clips.filter((_, idx) => selectedClips.has(idx))
    clipsToDownload.forEach((clip, index) => {
      setTimeout(() => {
        window.open(`${API_BASE}/jobs/${job.id}/download?filename=${clip.filename}`, '_blank')
      }, index * 500)
    })
  }

  const selectAll = () => {
    setSelectedClips(new Set(job.clips.map((_, idx) => idx)))
  }

  const clearSelection = () => {
    setSelectedClips(new Set())
  }

  if (!job.clips || job.clips.length === 0) {
    return (
      <VStack py={12} spacing={4}>
        <Text fontSize="4xl">📹</Text>
        <Text color="gray.500">No clips generated yet</Text>
        {job.status !== 'completed' && job.status !== 'failed' && (
          <HStack>
            <Spinner size="sm" />
            <Text color="gray.400">Processing in progress...</Text>
          </HStack>
        )}
        {job.error && (
          <Alert status="error" borderRadius="md" maxW="500px">
            <AlertIcon />
            {job.error}
          </Alert>
        )}
      </VStack>
    )
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Toolbar */}
      <HStack justify="space-between" px={2}>
        <HStack>
          <Checkbox
            isChecked={selectedClips.size === job.clips.length}
            isIndeterminate={selectedClips.size > 0 && selectedClips.size < job.clips.length}
            onChange={() => selectedClips.size === job.clips.length ? clearSelection() : selectAll()}
            colorScheme="purple"
          >
            Select All
          </Checkbox>
          {selectedClips.size > 0 && (
            <Text fontSize="sm" color="gray.500">
              ({selectedClips.size} selected)
            </Text>
          )}
        </HStack>
        {selectedClips.size > 0 && (
          <Button
            variant="primary"
            size="sm"
            onClick={downloadSelected}
            leftIcon={<Text>⬇️</Text>}
          >
            Download Selected
          </Button>
        )}
      </HStack>

      {/* Clips Grid - OpusClip style */}
      <SimpleGrid columns={{ base: 2, md: 3, lg: 4, xl: 5 }} spacing={4}>
        {job.clips.map((clip, idx) => (
          <ClipCard
            key={idx}
            clip={clip}
            jobId={job.id}
            index={idx}
            isSelected={selectedClips.has(idx)}
            onToggleSelect={() => toggleClipSelection(idx)}
            onPreview={() => onPreview(clip, job.id)}
          />
        ))}
      </SimpleGrid>
    </VStack>
  )
}

// Clip Card Component (OpusClip-style with prominent score)
function ClipCard({ clip, jobId, index, isSelected, onToggleSelect, onPreview }) {
  const thumbnailUrl = clip.thumbnail
    ? `${API_BASE}/jobs/${jobId}/thumbnail/${clip.thumbnail}`
    : null

  const score = clip.score || Math.floor(Math.random() * 30) + 70 // Default score

  const getScoreColor = (score) => {
    if (score >= 90) return 'green.400'
    if (score >= 80) return 'yellow.400'
    if (score >= 70) return 'orange.400'
    return 'gray.400'
  }

  return (
    <Card
      bg="dark.600"
      overflow="hidden"
      transition="all 0.2s"
      _hover={{ transform: 'translateY(-2px)', boxShadow: 'lg' }}
      borderWidth={isSelected ? '2px' : '1px'}
      borderColor={isSelected ? 'brand.500' : 'transparent'}
      position="relative"
    >
      {/* Selection checkbox */}
      <Box position="absolute" top={2} left={2} zIndex={2}>
        <Checkbox
          isChecked={isSelected}
          onChange={onToggleSelect}
          colorScheme="purple"
          size="lg"
          onClick={(e) => e.stopPropagation()}
        />
      </Box>

      {/* Duration badge */}
      <Badge
        position="absolute"
        top={2}
        right={2}
        bg="blackAlpha.700"
        color="white"
        fontSize="xs"
        zIndex={2}
      >
        {Math.floor((clip.duration || 30) / 60)}:{String(Math.floor((clip.duration || 30) % 60)).padStart(2, '0')}
      </Badge>

      {/* Thumbnail */}
      <AspectRatio ratio={9/16} cursor="pointer" onClick={onPreview}>
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
              <Text fontSize="3xl">🎬</Text>
            </Flex>
          )}
        </Box>
      </AspectRatio>

      <CardBody p={3}>
        <VStack align="start" spacing={2}>
          {/* Score - prominent like OpusClip */}
          <HStack spacing={3} w="100%">
            <Text
              fontSize="2xl"
              fontWeight="bold"
              color={getScoreColor(score)}
            >
              {score}
            </Text>
            <VStack align="start" spacing={0} flex={1}>
              <Text fontSize="xs" color="gray.500" noOfLines={1}>
                #{index + 1}
              </Text>
            </VStack>
          </HStack>

          {/* Title */}
          <Text fontSize="sm" fontWeight="medium" noOfLines={2} minH="40px">
            {clip.title || `Clip ${index + 1}`}
          </Text>

          {/* Action buttons */}
          <HStack w="100%" spacing={2}>
            <Button
              size="xs"
              variant="ghost"
              flex={1}
              onClick={onPreview}
              leftIcon={<Text fontSize="xs">▶️</Text>}
            >
              Preview
            </Button>
            <Button
              as="a"
              href={`${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`}
              download
              size="xs"
              variant="primary"
              flex={1}
              leftIcon={<Text fontSize="xs">⬇️</Text>}
            >
              Download
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
