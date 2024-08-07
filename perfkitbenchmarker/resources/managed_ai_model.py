# Copyright 2024 PerfKitBenchmarker Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A managed AI model resource.

A managed AI model uses a platform like Vertex AI or Sagemaker to manage the
resource, but the customer pays for the underlying resources it runs on, rather
than simply for calls like with an API. This also gives the customer more
control & ownership.
"""

from absl import flags
from perfkitbenchmarker import errors
from perfkitbenchmarker import resource

FLAGS = flags.FLAGS


class BaseManagedAiModel(resource.BaseResource):
  """A managed AI model."""

  RESOURCE_TYPE = 'BaseManagedAiModel'
  REQUIRED_ATTRS = ['CLOUD']

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if not FLAGS.zone:
      raise errors.Setup.InvalidConfigurationError(
          'Zone is required for Managed AI models but was not set.'
      )
    self.zone: str = FLAGS.zone[0]


def GetManagedAiModelClass(
    cloud: str,
) -> resource.AutoRegisterResourceMeta | None:
  """Gets the managed AI model class for the given cloud."""
  return resource.GetResourceClass(
      BaseManagedAiModel, CLOUD=cloud
  )
