import { useState } from 'react'
import {
  Box,
  VStack,
  Textarea,
  Button,
  Text,
  Container,
  Heading,
} from '@chakra-ui/react'
import axios from 'axios'

function App() {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async () => {
    if (!prompt.trim()) {
      return
    }

    setIsLoading(true)
    try {
      const { data } = await axios.post('http://localhost:2108/api/chat', {
        prompt: prompt.trim()
      })
      setResponse(data.response)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Container maxW="container.md" py={8}>
      <VStack spacing={6} align="stretch">
        <Heading as="h1" size="xl" textAlign="center">
          LLM Playground
        </Heading>
        
        <Box>
          <Text mb={2} fontWeight="bold">Prompt:</Text>
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter your prompt here..."
            size="lg"
            rows={5}
          />
        </Box>

        <Button
          colorScheme="blue"
          onClick={handleSubmit}
          isLoading={isLoading}
          loadingText="Generating..."
        >
          Generate Response
        </Button>

        {response && (
          <Box borderWidth={1} p={4} borderRadius="md">
            <Text mb={2} fontWeight="bold">Response:</Text>
            <Text whiteSpace="pre-wrap">{response}</Text>
          </Box>
        )}
      </VStack>
    </Container>
  )
}

export default App