import { useState, useEffect } from 'react'
import {
  Box, Container, VStack, HStack, Heading, Text, Input, Button,
  Card, CardBody, Badge, Progress, useDisclosure, Modal, ModalOverlay,
  ModalContent, ModalHeader, ModalBody, ModalFooter, SimpleGrid, Image,
  Flex, Spinner, Alert, AlertIcon, AspectRatio, Switch, FormControl,
  FormLabel, Divider, Link
} from '@chakra-ui/react'

const API_BASE = '/api'

interface Job {
  id: string
  url: string
  status: string
  progress: number
  created_at: string
  updated_at: string
  error?: string
  chapters?: Chapter[]
  clips?: Clip[]
}

interface Chapter {
  id: string
  title: string
  start: number
  end: number
  duration: number
  summary?: string
  confidence?: number
  hooks?: string[]
}

interface Clip {
  filename: string
  title: string
  start: number
  end: number
  duration: number
  thumbnail?: string
  score?: number
}

function App() {
  const [url, setUrl] = useState('')
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [chapterSelectJob, setChapterSelectJob] = useState<Job | null>(null)
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set())

  const [aiProviders, setAiProviders] = useState<any[]>([])
  const [currentProvider, setCurrentProvider] = useState('none')

  const { isOpen: isDetailOpen, onOpen: onDetailOpen, onClose: onDetailClose } = useDisclosure()
  const { isOpen: isChapterOpen, onOpen: onChapterOpen, onClose: onChapterClose } = useDisclosure()
  const { isOpen: isSettingsOpen, onOpen: onSettingsOpen, onClose: onSettingsClose } = useDisclosure()

  useEffect(() => {
    fetchJobs()
    fetchAiProviders()
    const interval = setInterval(fetchJobs, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const readyJob = jobs.find(j => j.status === 'chapters_ready')
    if (readyJob && !chapterSelectJob) {
      fetchChapters(readyJob.id)
      setChapterSelectJob(readyJob)
      onChapterOpen()
    }
  }, [jobs, chapterSelectJob])

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs`)
      if (res.ok) {
        const data = await res.json()
        setJobs(data)
      }
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    }
  }

  const fetchChapters = async (jobId: string) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/chapters`)
      if (res.ok) {
        const data = await res.json()
        setChapters(data)
      }
    } catch (err) {
      console.error('Failed to fetch chapters:', err)
    }
  }

  const fetchAiProviders = async () => {
    try {
      const res = await fetch(`${API_BASE}/ai-providers`)
      if (res.ok) {
        const data = await res.json()
        setAiProviders(data.providers)
        setCurrentProvider(data.current_provider)
      }
    } catch (err) {
      console.error('Failed to fetch AI providers:', err)
    }
  }

  const submitJob = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim() || loading) return

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() })
      })
      if (res.ok) {
        setUrl('')
        fetchJobs()
      }
    } catch (err) {
      console.error('Failed to submit job:', err)
    }
    setLoading(false)
  }

  const deleteJob = async (jobId: string, e?: React.MouseEvent) => {
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
  }

  const handleSelectChapters = async () => {
    if (!chapterSelectJob || selectedChapters.size === 0) return

    try {
      await fetch(`${API_BASE}/jobs/${chapterSelectJob.id}/select-chapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_ids: Array.from(selectedChapters),
          options: {}
        })
      })
      onChapterClose()
      setChapterSelectJob(null)
      setSelectedChapters(new Set())
      fetchJobs()
    } catch (err) {
      console.error('Failed to select chapters:', err)
    }
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
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

  const getThumbnail = (url: string) => {
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s?]+)/)
    return match ? `https://img.youtube.com/vi/${match[1]}/hqdefault.jpg` : null
  }

  return (
    <Box minH="100vh" bg="gray.900" py={8}>
      <Container maxW="7xl">
        {/* Header */}
        <VStack spacing={2} mb={10}>
          <HStack>
            <Heading size="2xl" bgGradient="linear(to-r, cyan.400, purple.400)" bgClip="text">
              Auto Clipper
            </Heading>
            <Button variant="ghost" onClick={onSettingsOpen}>⚙️</Button>
          </HStack>
          <Badge colorScheme="purple">No recurring fees - Run locally</Badge>
        </VStack>

        {/* Submit Form */}
        <Card bg="gray.800" mb={8}>
          <CardBody>
            <form onSubmit={submitJob}>
              <HStack gap={4}>
                <Input
                  placeholder="Paste YouTube URL here..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                />
                <Button type="submit" isLoading={loading} loadingText="Submitting" colorScheme="purple">
                  Create Clip
                </Button>
              </HStack>
            </form>
          </CardBody>
        </Card>

        {/* Projects Grid */}
        <Heading size="lg" mb={6}>All projects ({jobs.length})</Heading>

        {jobs.length === 0 ? (
          <Card bg="gray.800" p={12}>
            <Text textAlign="center" color="gray.500">No projects yet. Paste a URL to get started!</Text>
          </Card>
        ) : (
          <SimpleGrid columns={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing={4}>
            {jobs.map(job => {
              const thumbnail = getThumbnail(job.url)
              const needsSelection = job.status === 'chapters_ready'

              return (
                <Card
                  key={job.id}
                  bg="gray.800"
                  cursor="pointer"
                  onClick={() => {
                    if (needsSelection) {
                      fetchChapters(job.id)
                      setChapterSelectJob(job)
                      onChapterOpen()
                    } else {
                      setSelectedJob(job)
                      onDetailOpen()
                    }
                  }}
                  _hover={{ transform: 'translateY(-4px)' }}
                  transition="all 0.2s"
                >
                  <AspectRatio ratio={16 / 9}>
                    <Box bg="gray.700">
                      {thumbnail ? (
                        <Image src={thumbnail} alt="" objectFit="cover" w="100%" h="100%" />
                      ) : (
                        <Flex align="center" justify="center" h="100%">🎬</Flex>
                      )}

                      {job.status !== 'completed' && job.status !== 'failed' && (
                        <Flex
                          position="absolute"
                          inset={0}
                          bg="blackAlpha.700"
                          align="center"
                          justify="center"
                        >
                          <Spinner />
                        </Flex>
                      )}

                      {needsSelection && (
                        <Flex
                          position="absolute"
                          inset={0}
                          bg="blackAlpha.700"
                          align="center"
                          justify="center"
                        >
                          <Text fontSize="2xl">✨</Text>
                        </Flex>
                      )}
                    </Box>
                  </AspectRatio>

                  <CardBody p={3}>
                    <VStack align="start" spacing={2}>
                      <Text fontSize="sm" noOfLines={2}>
                        {job.url.slice(0, 50)}...
                      </Text>
                      <HStack justify="space-between" w="100%">
                        <Badge colorScheme={getStatusColor(job.status)}>{job.status}</Badge>
                        <Button
                          size="xs"
                          variant="ghost"
                          colorScheme="red"
                          onClick={(e) => deleteJob(job.id, e)}
                        >
                          🗑️
                        </Button>
                      </HStack>
                    </VStack>
                  </CardBody>
                </Card>
              )
            })}
          </SimpleGrid>
        )}
      </Container>

      {/* Chapter Selection Modal */}
      <Modal isOpen={isChapterOpen} onClose={onChapterClose} size="2xl">
        <ModalOverlay />
        <ModalContent bg="gray.800">
          <ModalHeader>Select Chapters to Clip</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={4} align="stretch">
              <HStack justify="space-between">
                <Text color="gray.400">Choose which chapters to convert</Text>
                <Button size="sm" onClick={() => setSelectedChapters(new Set(chapters.map(c => c.id)))}>
                  Select All
                </Button>
              </HStack>

              {selectedChapters.size > 0 && (
                <Alert status="info">
                  {selectedChapters.size} chapter{selectedChapters.size !== 1 ? 's' : ''} selected
                </Alert>
              )}

              <VStack spacing={2} maxH="400px" overflowY="auto">
                {chapters.map((chapter, i) => (
                  <Card
                    key={chapter.id}
                    bg={selectedChapters.has(chapter.id) ? 'purple.900' : 'gray.700'}
                    cursor="pointer"
                    onClick={() => {
                      const next = new Set(selectedChapters)
                      if (next.has(chapter.id)) next.delete(chapter.id)
                      else next.add(chapter.id)
                      setSelectedChapters(next)
                    }}
                  >
                    <CardBody py={3} px={4}>
                      <HStack justify="space-between">
                        <HStack>
                          <Badge>#{i + 1}</Badge>
                          <Text fontWeight="semibold">{chapter.title}</Text>
                        </HStack>
                        <Text>{Math.floor(chapter.duration / 60)}:{String(Math.floor(chapter.duration % 60)).padStart(2, '0')}</Text>
                      </HStack>
                    </CardBody>
                  </Card>
                ))}
              </VStack>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" onClick={onChapterClose}>Cancel</Button>
            <Button
              colorScheme="purple"
              isDisabled={selectedChapters.size === 0}
              onClick={handleSelectChapters}
            >
              Create {selectedChapters.size} Clip{selectedChapters.size !== 1 ? 's' : ''}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Settings Modal - Simplified */}
      <Modal isOpen={isSettingsOpen} onClose={onSettingsClose} size="lg">
        <ModalOverlay />
        <ModalContent bg="gray.800">
          <ModalHeader>Settings</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={4}>
              <FormControl display="flex" alignItems="center" justifyContent="space-between">
                <FormLabel mb="0">AI Provider</FormLabel>
                <Badge colorScheme="cyan">{currentProvider}</Badge>
              </FormControl>
              <Text fontSize="sm" color="gray.400">
                API keys can be set via environment variables or API.
              </Text>
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </Box>
  )
}

export default App
